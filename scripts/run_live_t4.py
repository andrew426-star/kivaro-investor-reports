"""Live T4 adapter: feed real-time ES bars to BeginnerTrader and route signals.

Defaults to T4 simulator + dry-run (no orders submitted). Set --live-orders only
after Tyson confirms simulator behavior and authorizes live execution.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from trading_agent.t4_client import T4Client, T4ClientConfig, LiveBar
from trading_agent.trader import BeginnerTrader, STARTING_CAPITAL


class LiveTraderBridge:
    def __init__(self, client: T4Client, agent: BeginnerTrader, dry_run: bool = True):
        self.client = client
        self.agent = agent
        self.dry_run = dry_run
        self.actions: list[dict] = []
        client.on_bar_complete = self._on_bar_complete_sync

    def _on_bar_complete_sync(self, bar: LiveBar, client: T4Client):
        # schedule async handling
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.on_bar_complete(bar))
        except RuntimeError:
            pass

    async def on_bar_complete(self, bar: LiveBar):
        ts = pd.Timestamp(bar.t, unit="ms", tz="UTC")
        lookback = self.client.aggregator.lookback_df(30)
        if lookback.empty or len(lookback) < 3:
            return
        bar_s = pd.Series({"open": bar.o, "high": bar.h, "low": bar.l, "close": bar.c, "volume": bar.v})
        action = self.agent.on_bar(bar_s, lookback.iloc[:-1] if len(lookback) > 1 else lookback, ts)
        if not action:
            return
        record = {"time": ts.isoformat(), "bar_close": bar.c, "action": action, "net_pos_state": self.agent.state.position}
        self.actions.append(record)
        self.client.log(f"AGENT ACTION {action} agent_pos={self.agent.state.position} dry_run={self.dry_run}", "warn")
        if self.dry_run:
            return
        await self._route_action(action)

    async def _route_action(self, action: dict):
        # Basic routing: entry -> market in agent direction; exits managed by agent internally,
        # but live position sync should be reconciled. This is intentionally conservative.
        act = action.get("action")
        if act in ("ENTRY", "REVENGE_ENTRY"):
            side = action.get("side")
            qty = abs(self.agent.state.position) or self.agent.state.contracts or 1
            if side:
                await self.client.submit_market(side, qty, tag=f"TJ-{act}")
        elif act == "EXIT":
            # In dry-run-safe live mode, only flatten if our tracked net matches intent.
            # Do not auto-flatten blindly; real T4 brackets/fills need reconciliation.
            self.client.log("Agent EXIT signaled; reconcile with T4 position/brackets before live flattening.", "warn")


def parse_args():
    p = argparse.ArgumentParser(description="Run BeginnerTrader against T4 simulator/live feed")
    p.add_argument("--api-key", default=os.environ.get("T4_API_KEY", ""), help="T4 API key (or set T4_API_KEY)")
    p.add_argument("--env", choices=["sim"], default="sim", help="T4 environment (sim only for now)")
    p.add_argument("--live-orders", action="store_true", help="Submit real/sim orders. Default is dry-run signal logging.")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--starting-capital", type=float, default=STARTING_CAPITAL)
    p.add_argument("--stop-min", type=float, default=12.0)
    p.add_argument("--stop-max", type=float, default=25.0)
    p.add_argument("--target-min", type=float, default=4.0)
    p.add_argument("--target-max", type=float, default=8.0)
    p.add_argument("--size2-prob", type=float, default=0.6)
    p.add_argument("--entry-lookback", type=int, default=4)
    p.add_argument("--drag-prob", type=float, default=0.85)
    p.add_argument("--remove-prob", type=float, default=0.7)
    p.add_argument("--revenge-prob", type=float, default=0.75)
    p.add_argument("--actions-out", default="results/live_actions.jsonl")
    return p.parse_args()


async def main():
    args = parse_args()
    if not args.api_key:
        raise SystemExit("Missing T4 API key. Pass --api-key or set T4_API_KEY. Do not commit keys.")

    dry_run = not args.live_orders
    config = T4ClientConfig(api_key=args.api_key, env=args.env, dry_run=dry_run)
    client = T4Client(config)
    agent = BeginnerTrader(
        starting_capital=args.starting_capital,
        seed=args.seed,
        stop_min=args.stop_min,
        stop_max=args.stop_max,
        target_min=args.target_min,
        target_max=args.target_max,
        size2_prob=args.size2_prob,
        entry_lookback=args.entry_lookback,
        drag_prob=args.drag_prob,
        remove_prob=args.remove_prob,
        revenge_prob=args.revenge_prob,
    )
    bridge = LiveTraderBridge(client, agent, dry_run=dry_run)
    out_path = Path(args.actions_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    async def write_actions():
        last = 0
        while not client._stop.is_set():
            await asyncio.sleep(5)
            if len(bridge.actions) > last:
                with out_path.open("a", encoding="utf-8") as f:
                    for rec in bridge.actions[last:]:
                        f.write(json.dumps(rec, default=str) + "\n")
                last = len(bridge.actions)

    def _stop(*_):
        client.log("Stopping live adapter...", "warn")
        client._stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _stop)
        except Exception:
            pass

    writer = asyncio.create_task(write_actions())
    try:
        await client.connect()
    finally:
        client._stop.set()
        writer.cancel()
        # final flush
        if bridge.actions:
            with out_path.open("a", encoding="utf-8") as f:
                for rec in bridge.actions:
                    pass
        stats = agent.get_stats()
        client.log(f"Final agent stats snapshot: {json.dumps(stats, default=str)}")
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
