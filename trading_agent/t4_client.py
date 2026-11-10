"""T4 simulator/live WebSocket client for ES trading (extracted from ES_TJ_Trader_6.1.html).

Protocol: protobuf binary over WebSocket (t4proto.v2). Auth via loginRequest.apiKey.
Default target is the T4 simulator (sim.t4login.com). Verify with Tyson before live use.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import websockets

T4_ENV = {
    "sim": {"ws": "wss://wss-sim.t4login.com/v2", "api": "https://api-sim.t4login.com"},
}
T4_BUILD = "2026-11-03 separate-brackets-sim+t4"
EXCHANGE_ID = "CME_Eq"
CONTRACT_ID = "ES"
TICK = 0.25
POINT_VALUE = 50.0


def _load_proto():
    desc_path = Path(__file__).with_name("t4_desc.json")
    raw = desc_path.read_bytes()
    for bom in (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff"):
        if raw.startswith(bom):
            raw = raw[len(bom):]
    desc_json = json.loads(raw.decode("utf-8"))
    # The descriptor is a protobufjs JSON root; python's built-in json_format doesn't parse it
    # directly as FileDescriptorSet. Use descriptor_pool from generated-like approach is complex.
    # Instead, keep a thin dynamic approach via protobuf reflection is not available from JSON root.
    # We fall back to protobufjs-like handling by using the `protobuf` npm package? No, Python.
    # Practical fallback: use `blackboxprotobuf`? not installed. So we implement a minimal
    # encoder/decoder by shelling to node with protobufjs for this environment? Node is installed.
    raise RuntimeError(
        "T4_DESC is protobufjs JSON; Python needs generated pb2 or a Node bridge. "
        "Use T4NodeBridge (Node/protobufjs) in this repo."
    )


class T4NodeBridge:
    """Bridge to Node+protobufjs for encoding/decoding T4 protobuf messages."""

    def __init__(self, desc_path: Optional[Path] = None):
        self.desc_path = desc_path or Path(__file__).with_name("t4_desc.json")
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()

    async def start(self):
        bridge_js = Path(__file__).with_name("t4_proto_bridge.js")
        if not bridge_js.exists():
            self._write_bridge(bridge_js)
        self.proc = await asyncio.create_subprocess_exec(
            "node", str(bridge_js), str(self.desc_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # wait for ready
        line = await asyncio.wait_for(self.proc.stdout.readline(), 10)
        msg = json.loads(line)
        if not msg.get("ok"):
            raise RuntimeError(f"proto bridge failed: {msg}")

    def _write_bridge(self, path: Path):
        path.write_text(r'''// T4 protobuf bridge: stdin JSON lines -> stdout JSON lines (base64 binary for send)
const fs = require('fs');
const path = require('path');
const descPath = process.argv[2];
let protobuf;
try { protobuf = require('protobufjs'); } catch (e) {
  try { protobuf = require(path.join(process.cwd(), 'node_modules', 'protobufjs')); } catch (e2) {
    console.log(JSON.stringify({ok:false,error:'protobufjs not found. npm i protobufjs'}));
    process.exit(1);
  }
}
const desc = JSON.parse(fs.readFileSync(descPath, 'utf8'));
const root = protobuf.Root.fromJSON(desc);
const CM = root.lookupType('t4proto.v2.service.ClientMessage');
const SM = root.lookupType('t4proto.v2.service.ServerMessage');
const OPT = {defaults:true, longs:Number, enums:Number, oneofs:true};
console.log(JSON.stringify({ok:true}));
const rl = require('readline').createInterface({input: process.stdin});
rl.on('line', (line) => {
  try {
    const req = JSON.parse(line);
    if (req.op === 'encode') {
      const err = CM.verify(req.msg);
      if (err) return console.log(JSON.stringify({id:req.id,error:err}));
      const buf = CM.encode(CM.fromObject(req.msg)).finish();
      console.log(JSON.stringify({id:req.id,bin:Buffer.from(buf).toString('base64')}));
    } else if (req.op === 'decode') {
      const buf = Buffer.from(req.bin, 'base64');
      const msg = SM.toObject(SM.decode(buf), OPT);
      console.log(JSON.stringify({id:req.id,msg}));
    } else if (req.op === 'ping') {
      console.log(JSON.stringify({id:req.id,ok:true}));
    }
  } catch (e) {
    console.log(JSON.stringify({id:(req&&req.id)||null,error:String(e&&e.stack||e)}));
  }
});
''', encoding='utf-8')

    async def _rpc(self, op: str, **kwargs) -> Any:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("bridge not started")
        async with self._lock:
            rid = str(uuid.uuid4())
            req = {"id": rid, "op": op, **kwargs}
            self.proc.stdin.write((json.dumps(req) + "\n").encode())
            await self.proc.stdin.drain()
            line = await asyncio.wait_for(self.proc.stdout.readline(), 30)
            resp = json.loads(line)
            if resp.get("id") != rid:
                # resync read (simple)
                pass
            if "error" in resp:
                raise RuntimeError(resp["error"])
            return resp

    async def encode(self, msg: dict) -> bytes:
        resp = await self._rpc("encode", msg=msg)
        import base64
        return base64.b64decode(resp["bin"])

    async def decode(self, data: bytes) -> dict:
        import base64
        resp = await self._rpc("decode", bin=base64.b64encode(data).decode())
        return resp["msg"]

    async def stop(self):
        if self.proc:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            self.proc.terminate()


@dataclass
class LiveBar:
    t: int  # epoch ms, bar start
    o: float
    h: float
    l: float
    c: float
    v: float = 0.0


class BarAggregator:
    """Aggregate trade prints into 5-minute bars (UTC)."""

    def __init__(self, bar_ms: int = 300_000):
        self.bar_ms = bar_ms
        self.current: Optional[LiveBar] = None
        self.history: list[LiveBar] = []
        self.pscale: Optional[float] = None

    def scale_price(self, v: float) -> float:
        if v is None:
            return float("nan")
        if self.pscale is None and v > 100000:
            self.pscale = 100.0
        return v / (self.pscale or 1.0)

    def _num(self, d: Any) -> float:
        if not d:
            return float("nan")
        try:
            v = float(d.get("value") if isinstance(d, dict) else d)
            return v
        except Exception:
            return float("nan")

    def on_trade(self, px: float, vol: float, now_ms: Optional[int] = None) -> Optional[LiveBar]:
        now_ms = now_ms or int(time.time() * 1000)
        bt = (now_ms // self.bar_ms) * self.bar_ms
        completed = None
        if self.current and self.current.t < bt:
            completed = self.current
            self.history.append(completed)
            self.history = self.history[-2000:]
            self.current = None
        if not self.current or self.current.t < bt:
            self.current = LiveBar(t=bt, o=px, h=px, l=px, c=px, v=0.0)
        b = self.current
        b.h = max(b.h, px)
        b.l = min(b.l, px)
        b.c = px
        b.v += vol or 0.0
        return completed

    def lookback_df(self, n: int = 30):
        import pandas as pd
        bars = list(self.history[-n:])
        if self.current:
            bars.append(self.current)
        if not bars:
            return pd.DataFrame()
        return pd.DataFrame([{ "open": b.o, "high": b.h, "low": b.l, "close": b.c, "volume": b.v} for b in bars])


@dataclass
class T4ClientConfig:
    api_key: str
    env: str = "sim"
    ws_url: Optional[str] = None
    api_url: Optional[str] = None
    exchange_id: str = EXCHANGE_ID
    contract_id: str = CONTRACT_ID
    market_id: Optional[str] = None  # override
    account_id: Optional[str] = None
    dry_run: bool = True  # route signals to callbacks, do not submit orders


class T4Client:
    def __init__(self, config: T4ClientConfig):
        self.config = config
        self.bridge = T4NodeBridge()
        self.ws = None
        self.status = "off"
        self.account_id: Optional[str] = config.account_id
        self.market_id: Optional[str] = config.market_id
        self.market_alt: Optional[str] = None
        self.accounts: list[dict] = []
        self.aggregator = BarAggregator(bar_ms=300_000)
        self.net = 0
        self.raw_orders: dict[str, dict] = {}
        self.on_bar_complete: Optional[Callable[[LiveBar, Any], Any]] = None
        self.on_log: Optional[Callable[[str, str], Any]] = None
        self._hb_task = None
        self._stop = asyncio.Event()

    def log(self, msg: str, kind: str = "info"):
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] [{kind}] {msg}"
        print(line)
        if self.on_log:
            self.on_log(msg, kind)

    async def connect(self):
        env = T4_ENV.get(self.config.env, T4_ENV["sim"])
        ws_url = self.config.ws_url or env["ws"]
        await self.bridge.start()
        self.log(f"Connecting to {ws_url} (env={self.config.env}, dry_run={self.config.dry_run})")
        self.status = "connecting"
        async with websockets.connect(ws_url, max_size=8 * 1024 * 1024) as ws:
            self.ws = ws
            await self._send({"loginRequest": {"apiKey": self.config.api_key, "priceFormat": 1}})
            self._hb_task = asyncio.create_task(self._heartbeat())
            try:
                async for raw in ws:
                    if self._stop.is_set():
                        break
                    msg = await self.bridge.decode(raw)
                    await self._handle(msg)
            finally:
                self._hb_task.cancel()
                self.status = "off"

    async def _send(self, obj: dict):
        if not self.ws:
            raise RuntimeError("not connected")
        data = await self.bridge.encode(obj)
        await self.ws.send(data)

    async def _heartbeat(self):
        while not self._stop.is_set():
            try:
                await asyncio.sleep(20)
                await self._send({"heartbeat": {"timestamp": int(time.time() * 1000)}})
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.log(f"heartbeat error: {e}", "warn")

    async def _handle(self, m: dict):
        payload = m.get("payload")
        if payload == "loginResponse":
            await self._on_login(m.get("loginResponse") or {})
        elif payload == "marketTrade":
            self._on_market_trade(m.get("marketTrade") or {})
        elif payload == "marketSnapshot":
            snap = m.get("marketSnapshot") or {}
            for x in snap.get("messages") or []:
                if x.get("marketTrade"):
                    self._on_market_trade(x["marketTrade"])
        elif payload == "accountSnapshot":
            s = m.get("accountSnapshot") or {}
            for x in s.get("messages") or []:
                if x.get("accountPosition"):
                    self._on_position(x["accountPosition"])
                elif x.get("orderStatus"):
                    self._on_order(x["orderStatus"])
        elif payload == "accountPosition":
            self._on_position(m.get("accountPosition") or {})
        elif payload == "accountPositionProfit":
            pass
        elif payload == "orderUpdate":
            self._on_order(m.get("orderUpdate") or {})
        elif payload == "marketSubscribeReject":
            self.log(f"Market subscribe rejected: {m.get('marketSubscribeReject')}", "err")
        elif payload == "orderBatchReject":
            self.log(f"Order batch rejected: {m.get('orderBatchReject')}", "err")

    async def _on_login(self, r: dict):
        res = r.get("result", 0)
        if res != 0:
            self.log(f"Login refused: result={res} error={r.get('errorMessage')}", "err")
            self.status = "error"
            self._stop.set()
            return
        self.accounts = r.get("accounts") or []
        if not self.account_id and self.accounts:
            self.account_id = self.accounts[0].get("accountId")
        self.log(f"Logged in. accounts={len(self.accounts)} account_id={self.account_id}")
        await self._send({"accountSubscribe": {"subscribe": 2, "subscribeAllAccounts": True, "uplMode": 1}})
        market_id = self.config.market_id or self._front_month_id()
        self.market_id = market_id
        self.log(f"Subscribing market {self.config.exchange_id}/{self.config.contract_id} {market_id}")
        await self._send({
            "marketSubscribe": {
                "exchangeId": self.config.exchange_id,
                "contractId": self.config.contract_id,
                "marketId": market_id,
                "quotes": 2,
                "ticker": True,
            }
        })
        self.status = "live"

    def _front_month_id(self) -> str:
        codes = {3: "H", 6: "M", 9: "U", 12: "Z"}
        now = datetime.now(timezone.utc)
        for k in range(12):
            month = ((now.month - 1 + k) % 12) + 1
            year = now.year + ((now.month - 1 + k) // 12)
            if month not in codes:
                continue
            # 3rd Friday
            import calendar
            c = calendar.monthcalendar(year, month)
            fridays = [w[calendar.FRIDAY] for w in c if w[calendar.FRIDAY]]
            fri3 = datetime(year, month, fridays[2], tzinfo=timezone.utc)
            if now < fri3:
                return f"XCME_Eq {self.config.contract_id} ({codes[month]}{str(year)[2:]})"
        return "XCME_Eq ES (Z26)"

    def _mkt_ok(self, market_id: Optional[str]) -> bool:
        if not market_id or market_id == self.market_id or market_id == self.market_alt:
            return True
        if not self.market_alt and self.config.contract_id in (market_id or ""):
            self.market_alt = market_id
            self.log(f"Accepting alt market id {market_id}", "warn")
            return True
        return False

    def _num(self, d: Any) -> float:
        if not isinstance(d, dict):
            try:
                return float(d)
            except Exception:
                return float("nan")
        try:
            return float(d.get("value"))
        except Exception:
            return float("nan")

    def _on_market_trade(self, tr: dict):
        if not self._mkt_ok(tr.get("marketId")):
            return
        if tr.get("dueToSpread"):
            return
        px = self.aggregator.scale_price(self._num(tr.get("lastTradePrice")))
        vol = self._num(tr.get("lastTradeVolume")) or 0.0
        if not (px == px) or px <= 0:
            return
        completed = self.aggregator.on_trade(px, vol)
        if completed and self.on_bar_complete:
            self.on_bar_complete(completed, self)

    def _on_position(self, p: dict):
        if p.get("accountId") != self.account_id:
            return
        if not self._mkt_ok(p.get("marketId")) and p.get("contractId") != self.config.contract_id:
            return
        buys = int(p.get("buys") or 0)
        sells = int(p.get("sells") or 0)
        self.net = buys - sells
        self.log(f"Position update net={self.net} buys={buys} sells={sells}")

    def _on_order(self, ou: dict):
        if ou.get("accountId") != self.account_id:
            return
        uid = ou.get("uniqueId")
        if uid:
            self.raw_orders[uid] = ou
        status = ou.get("status")
        if status == 3:
            self.log(f"Order rejected: {ou.get('statusDetail')} tag={ou.get('tag')}", "err")

    async def submit_market(self, side: str, qty: int, tag: str = "TJ-ENTRY"):
        if self.config.dry_run:
            self.log(f"DRY RUN market {side} qty={qty} tag={tag}", "warn")
            return None
        if self.status != "live" or not self.account_id or not self.market_id:
            self.log("submit_market: not ready", "err")
            return None
        buy_sell = 1 if side.lower() in ("long", "buy") else 2
        order = {
            "buySell": buy_sell,
            "priceType": 0,  # MARKET
            "timeType": 0,
            "volume": {"value": str(qty)},
            "tag": tag,
            "ClOrdId": str(uuid.uuid4()),
        }
        await self._send({
            "orderSubmit": {
                "accountId": self.account_id,
                "marketId": self.market_id,
                "orderLink": 0,
                "manualOrderIndicator": True,
                "orders": [order],
            }
        })
        self.log(f"Submitted MARKET side={side} qty={qty}")
        return order["ClOrdId"]

    async def flatten(self):
        if self.config.dry_run:
            self.log(f"DRY RUN flatten net={self.net}", "warn")
            return
        if not self.net:
            return
        side = "short" if self.net > 0 else "long"
        qty = abs(self.net)
        buy_sell = 2 if self.net > 0 else 1
        order = {
            "buySell": buy_sell,
            "priceType": 16,  # FLATTEN
            "timeType": 0,
            "volume": {"value": str(qty)},
            "tag": "TJ-FLAT",
            "ClOrdId": str(uuid.uuid4()),
        }
        await self._send({
            "orderSubmit": {
                "accountId": self.account_id,
                "marketId": self.market_id,
                "orderLink": 0,
                "manualOrderIndicator": True,
                "orders": [order],
            }
        })
        self.log("Submitted FLATTEN")

    async def stop(self):
        self._stop.set()
        await self.bridge.stop()
