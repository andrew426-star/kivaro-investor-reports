"""Run max-loss backtest with slippage modeling and aggressive param search.

Optimizes for worst (most negative) average trade net P/L on forward test.
Supports configurable slippage (ticks per side, 1 tick = $12.50/contract).
"""
import sys
import argparse
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from trading_agent.backtest import (
    resample_to_5min, run_backtest, compute_daily_pnl, compute_equity_curve
)


def load_full_data():
    t = pq.read_table('data/es_front_month_24h.parquet',
                      columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    front = t.to_pandas().sort_values('timestamp').reset_index(drop=True)
    return resample_to_5min(front)


def trade_rows(trade_log):
    rows = []
    for t in trade_log:
        rows.append({
            'entry_time': t.entry_time, 'exit_time': t.exit_time,
            'side': t.side, 'contracts': t.contracts, 'session': t.session,
            'entry_price': t.entry_price, 'exit_price': t.exit_price,
            'fill_entry_price': t.fill_entry_price, 'fill_exit_price': t.fill_exit_price,
            'target_price': t.target_price, 'stop_price': t.stop_price,
            'pnl_gross': t.pnl_gross, 'commission': t.commission,
            'slippage': t.slippage, 'pnl_net': t.pnl_net,
            'exit_reason': t.exit_reason, 'mistake_type': t.mistake_type,
            'max_adverse_excursion': t.max_adverse_excursion,
            'max_favorable_excursion': t.max_favorable_excursion,
        })
    return rows


def summarize(result, best_params, meta_extra=None):
    stats = result['stats']
    log = result['trade_log']
    day = [t for t in log if t.session == 'day']
    night = [t for t in log if t.session == 'night']
    daily = compute_daily_pnl(log)
    return {
        'test_optimized': stats,
        'best_params': best_params,
        'daily_pnl': daily,
        'day_night': {
            'day_trades': len(day), 'night_trades': len(night),
            'day_avg_pnl': sum(t.pnl_net for t in day)/len(day) if day else 0,
            'night_avg_pnl': sum(t.pnl_net for t in night)/len(night) if night else 0,
        },
        'metadata': {
            'starting_capital': 50000,
            'commission_per_contract': 5.0,
            'es_point_value': 50.0,
            'es_tick_value': 12.50,
            'seed': 42,
            'objective': 'maximize average trade net loss (forward test optimized)',
            'trades_overnight': True,
            **(meta_extra or {}),
        },
    }


def run_grid(test_df, slippage_ticks, target_avg=None, min_trades=100):
    param_grid = [
        dict(stop_min=12, stop_max=25, target_min=4, target_max=8, size2_prob=0.6, entry_lookback=4, drag_prob=0.85, remove_prob=0.7, revenge_prob=0.75),
        dict(stop_min=15, stop_max=30, target_min=3, target_max=7, size2_prob=0.7, entry_lookback=3, drag_prob=0.9, remove_prob=0.75, revenge_prob=0.8),
        dict(stop_min=18, stop_max=35, target_min=3, target_max=6, size2_prob=0.8, entry_lookback=3, drag_prob=0.9, remove_prob=0.8, revenge_prob=0.85),
        dict(stop_min=20, stop_max=40, target_min=2, target_max=5, size2_prob=0.8, entry_lookback=2, drag_prob=0.95, remove_prob=0.85, revenge_prob=0.9),
        dict(stop_min=25, stop_max=45, target_min=2, target_max=4, size2_prob=0.9, entry_lookback=2, drag_prob=0.95, remove_prob=0.9, revenge_prob=0.9),
        dict(stop_min=30, stop_max=55, target_min=1, target_max=3, size2_prob=1.0, entry_lookback=2, drag_prob=0.98, remove_prob=0.95, revenge_prob=0.95),
        dict(stop_min=35, stop_max=60, target_min=1, target_max=2, size2_prob=1.0, entry_lookback=1, drag_prob=0.99, remove_prob=0.97, revenge_prob=0.97),
        dict(stop_min=40, stop_max=70, target_min=1, target_max=2, size2_prob=1.0, entry_lookback=1, drag_prob=1.0, remove_prob=0.98, revenge_prob=0.98),
        dict(stop_min=45, stop_max=80, target_min=0.5, target_max=1.5, size2_prob=1.0, entry_lookback=1, drag_prob=1.0, remove_prob=0.99, revenge_prob=0.99),
        dict(stop_min=50, stop_max=90, target_min=0.5, target_max=1.0, size2_prob=1.0, entry_lookback=1, drag_prob=1.0, remove_prob=1.0, revenge_prob=1.0),
    ]
    best, best_params, best_stats = None, None, None
    best_score = -1e18
    rows = []
    for i, p in enumerate(param_grid):
        params = {**p, 'slippage_ticks_per_side': slippage_ticks}
        result = run_backtest(test_df, starting_capital=50000, seed=42, agent_kwargs=params)
        s = result['stats']
        avg = s['avg_trade_net_pnl']
        ok = s['total_trades'] >= min_trades
        score = -avg if ok else -1e12
        rows.append({'i': i+1, 'avg': avg, 'trades': s['total_trades'], 'win': s['win_rate'], 'dd': s['max_drawdown'], 'end': s['ending_equity'], 'params': p})
        print(f"  [{i+1:02d}] avg=${avg:8.2f} trades={s['total_trades']:5d} win={s['win_rate']:5.1f}% dd=${s['max_drawdown']:10.0f} end=${s['ending_equity']:10.0f}")
        if score > best_score:
            best_score, best, best_params, best_stats = score, result, p, s
        if target_avg is not None and ok and avg <= target_avg:
            print(f"  -> target {target_avg} reached at grid {i+1}")
            return best, best_params, rows
    return best, best_params, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--slippage-ticks', type=float, default=1.0, help='Slippage ticks per side (ES tick=$12.50)')
    ap.add_argument('--target-avg', type=float, default=-900.0, help='Target avg trade net P/L (stop search when reached)')
    ap.add_argument('--sweep', action='store_true', help='Run slippage sweep 0..2 ticks with best params search')
    ap.add_argument('--out-prefix', default='max_loss_v2')
    args = ap.parse_args()

    print("=" * 70)
    print("MAX-LOSS AGENT v2 - Slippage + 2x Target Search")
    print("=" * 70)
    df_5min = load_full_data()
    test_start, test_end = '2026-04-27', '2026-10-26'
    test_df = df_5min[(df_5min['timestamp'] >= test_start) & (df_5min['timestamp'] <= test_end)].copy()
    print(f"Forward test: {test_start} to {test_end}, bars={len(test_df)}")

    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    if args.sweep:
        sweep = {}
        for slip in [0.0, 0.5, 1.0, 1.5, 2.0]:
            print(f"\n--- Slippage {slip} tick/side (${slip*12.5:.2f}/side, ${slip*25:.2f} RT/contract) ---")
            best, best_params, grid_rows = run_grid(test_df, slip, target_avg=None)
            s = best['stats']
            sweep[str(slip)] = {'avg_trade_net_pnl': s['avg_trade_net_pnl'], 'total_trades': s['total_trades'],
                                'win_rate': s['win_rate'], 'max_drawdown': s['max_drawdown'],
                                'ending_equity': s['ending_equity'], 'total_slippage': s['total_slippage'],
                                'best_params': best_params}
            print(f"  BEST @ {slip}t: avg=${s['avg_trade_net_pnl']:.2f} trades={s['total_trades']} win={s['win_rate']:.1f}% slip=${s['total_slippage']:.0f}")
        with open(output_dir / f'{args.out_prefix}_slippage_sweep.json', 'w') as f:
            json.dump(sweep, f, indent=2, default=str)
        print(f"\nSaved sweep: results/{args.out_prefix}_slippage_sweep.json")

    print(f"\n--- Primary run (slippage={args.slippage_ticks} tick/side, target={args.target_avg}) ---")
    best, best_params, grid_rows = run_grid(test_df, args.slippage_ticks, target_avg=args.target_avg)
    if best is None:
        print("No valid result found.")
        return
    stats = best['stats']
    print(f"\nBest params: {best_params}")
    print(f"Avg trade net P/L: ${stats['avg_trade_net_pnl']:.2f} (target {args.target_avg})")
    print(f"Trades: {stats['total_trades']} | Win: {stats['win_rate']:.1f}% | Total net: ${stats['total_pnl_net']:.2f}")
    print(f"Commission: ${stats['total_commission']:.2f} | Slippage: ${stats['total_slippage']:.2f} | Max DD: ${stats['max_drawdown']:.2f}")
    print(f"Ending equity: ${stats['ending_equity']:.2f} | Avg loss: ${stats['avg_loss']:.2f} | Largest loss: ${stats['largest_loss']:.2f}")
    log = best['trade_log']
    day = [t for t in log if t.session == 'day']
    night = [t for t in log if t.session == 'night']
    print(f"Day trades: {len(day)} avg=${(sum(t.pnl_net for t in day)/len(day)) if day else 0:.2f} | Night trades: {len(night)} avg=${(sum(t.pnl_net for t in night)/len(night)) if night else 0:.2f}")
    daily = compute_daily_pnl(log)
    if daily:
        ddf = pd.DataFrame(daily)
        print(f"Days: {len(ddf)} | Avg daily: ${ddf['pnl_net'].mean():.2f} | Worst day: ${ddf['pnl_net'].min():.2f}")
    eq = compute_equity_curve(best['equity_curve'])
    if len(eq):
        print(f"Peak equity: ${eq['equity'].max():.2f} | Valley: ${eq['equity'].min():.2f}")

    summary = summarize(best, best_params, {
        'test_period': f"{test_start} to {test_end}",
        'slippage_ticks_per_side': args.slippage_ticks,
        'slippage_per_side_usd': args.slippage_ticks * 12.50,
        'slippage_round_turn_usd_per_contract': args.slippage_ticks * 25.0,
        'target_avg_trade_net_pnl': args.target_avg,
        'target_reached': stats['avg_trade_net_pnl'] <= args.target_avg,
    })
    with open(output_dir / f'stats_{args.out_prefix}.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    pd.DataFrame(trade_rows(log)).to_parquet(output_dir / f'trade_log_{args.out_prefix}.parquet', index=False)
    eq.to_parquet(output_dir / f'equity_curve_{args.out_prefix}.parquet', index=False)
    print(f"\nSaved: results/stats_{args.out_prefix}.json, trade_log_{args.out_prefix}.parquet, equity_curve_{args.out_prefix}.parquet")


if __name__ == '__main__':
    main()
