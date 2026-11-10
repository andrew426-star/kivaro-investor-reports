"""Run max-loss backtest using existing front-month data (memory efficient)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
from trading_agent.backtest import (
    resample_to_5min, run_backtest, compute_daily_pnl, compute_equity_curve
)


def load_full_data():
    """Load 24-hour front-month ES data and resample to 5-min."""
    t = pq.read_table('data/es_front_month_24h.parquet',
                      columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    front = t.to_pandas()
    front = front.sort_values('timestamp').reset_index(drop=True)
    return resample_to_5min(front)


def main():
    print("=" * 60)
    print("MAX-LOSS BEGINNER AGENT - Forward Test Optimization")
    print("=" * 60)

    print("\nLoading ES front-month data...")
    df_5min = load_full_data()
    print(f"  5-min bars: {len(df_5min)}")
    print(f"  Date range: {df_5min['timestamp'].min()} to {df_5min['timestamp'].max()}")

    test_start = '2026-04-27'
    test_end = '2026-10-26'
    test_mask = (df_5min['timestamp'] >= test_start) & (df_5min['timestamp'] <= test_end)
    test_df = df_5min[test_mask].copy()
    print(f"\nForward test bars: {len(test_df)}")

    param_grid = [
        dict(stop_min=12, stop_max=25, target_min=4, target_max=8, size2_prob=0.6, entry_lookback=4, drag_prob=0.85, remove_prob=0.7, revenge_prob=0.75),
        dict(stop_min=15, stop_max=30, target_min=3, target_max=7, size2_prob=0.7, entry_lookback=3, drag_prob=0.9, remove_prob=0.75, revenge_prob=0.8),
        dict(stop_min=18, stop_max=35, target_min=3, target_max=6, size2_prob=0.8, entry_lookback=3, drag_prob=0.9, remove_prob=0.8, revenge_prob=0.85),
        dict(stop_min=20, stop_max=40, target_min=2, target_max=5, size2_prob=0.8, entry_lookback=2, drag_prob=0.95, remove_prob=0.85, revenge_prob=0.9),
        dict(stop_min=25, stop_max=45, target_min=2, target_max=4, size2_prob=0.9, entry_lookback=2, drag_prob=0.95, remove_prob=0.9, revenge_prob=0.9),
    ]

    best = None
    best_score = -999999
    best_params = None

    print("\nOptimizing on forward test (max avg trade net loss)...")
    for i, params in enumerate(param_grid):
        result = run_backtest(test_df, starting_capital=50000, seed=42, agent_kwargs=params)
        stats = result['stats']
        score = -stats['avg_trade_net_pnl'] if stats['total_trades'] >= 50 else 0
        print(f"  [{i+1}/{len(param_grid)}] avg_pnl=${stats['avg_trade_net_pnl']:.2f}, "
              f"trades={stats['total_trades']}, win%={stats['win_rate']:.1f}, "
              f"max_dd=${stats['max_drawdown']:.0f}, ending=${stats['ending_equity']:.0f}")
        if score > best_score:
            best_score = score
            best = result
            best_params = params

    print(f"\nBest params: {best_params}")
    print("\n" + "=" * 60)
    print("FORWARD TEST RESULTS (optimized for max loss)")
    print("=" * 60)
    stats = best['stats']
    print(f"  Total trades: {stats['total_trades']}")
    print(f"  Total net P/L: ${stats['total_pnl_net']:.2f}")
    print(f"  Average trade net P/L: ${stats['avg_trade_net_pnl']:.2f}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Total commission: ${stats['total_commission']:.2f}")
    print(f"  Max drawdown: ${stats['max_drawdown']:.2f}")
    print(f"  Starting capital: ${stats['starting_capital']:.2f}")
    print(f"  Ending equity: ${stats['ending_equity']:.2f}")
    print(f"  Avg win: ${stats['avg_win']:.2f}")
    print(f"  Avg loss: ${stats['avg_loss']:.2f}")
    print(f"  Largest win: ${stats['largest_win']:.2f}")
    print(f"  Largest loss: ${stats['largest_loss']:.2f}")
    print(f"  Sessions: {stats.get('session_counts', {})}")
    print(f"  Mistakes: {stats.get('mistake_counts', {})}")
    print(f"  Exit reasons: {stats.get('exit_counts', {})}")

    trade_log = best['trade_log']
    day_trades = [t for t in trade_log if t.session == 'day']
    night_trades = [t for t in trade_log if t.session == 'night']
    print(f"\n  Day trades: {len(day_trades)}, Night trades: {len(night_trades)}")
    if day_trades:
        print(f"  Day avg P/L: ${sum(t.pnl_net for t in day_trades)/len(day_trades):.2f}")
    if night_trades:
        print(f"  Night avg P/L: ${sum(t.pnl_net for t in night_trades)/len(night_trades):.2f}")

    daily = compute_daily_pnl(trade_log)
    if daily:
        daily_df = pd.DataFrame(daily)
        print(f"\n  Days with trades: {len(daily_df)}")
        print(f"  Avg daily P/L: ${daily_df['pnl_net'].mean():.2f}")
        print(f"  Worst day: ${daily_df['pnl_net'].min():.2f}")

    equity_df = compute_equity_curve(best['equity_curve'])
    if len(equity_df) > 0:
        print(f"  Peak equity: ${equity_df['equity'].max():.2f}")
        print(f"  Valley equity: ${equity_df['equity'].min():.2f}")

    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)

    trade_rows = []
    for t in trade_log:
        trade_rows.append({
            'entry_time': t.entry_time, 'exit_time': t.exit_time,
            'side': t.side, 'contracts': t.contracts,
            'entry_price': t.entry_price, 'exit_price': t.exit_price,
            'target_price': t.target_price, 'stop_price': t.stop_price,
            'pnl_gross': t.pnl_gross, 'commission': t.commission, 'pnl_net': t.pnl_net,
            'exit_reason': t.exit_reason, 'mistake_type': t.mistake_type,
            'max_adverse_excursion': t.max_adverse_excursion,
            'max_favorable_excursion': t.max_favorable_excursion,
            'session': t.session,
        })

    all_stats = {
        'test_optimized': stats,
        'best_params': best_params,
        'daily_pnl': daily,
        'day_night': {
            'day_trades': len(day_trades),
            'night_trades': len(night_trades),
            'day_avg_pnl': sum(t.pnl_net for t in day_trades)/len(day_trades) if day_trades else 0,
            'night_avg_pnl': sum(t.pnl_net for t in night_trades)/len(night_trades) if night_trades else 0,
        },
        'metadata': {
            'starting_capital': 50000,
            'commission_per_contract': 5.0,
            'es_point_value': 50.0,
            'test_period': f"{test_start} to {test_end}",
            'seed': 42,
            'objective': 'maximize average trade net loss (forward test optimized)',
            'trades_overnight': True,
        },
    }

    with open(output_dir / 'stats_max_loss.json', 'w') as f:
        json.dump(all_stats, f, indent=2, default=str)
    pd.DataFrame(trade_rows).to_parquet(output_dir / 'trade_log_max_loss.parquet', index=False)
    equity_df.to_parquet(output_dir / 'equity_curve_max_loss.parquet', index=False)

    print(f"\nSaved to results/stats_max_loss.json, trade_log_max_loss.parquet, equity_curve_max_loss.parquet")
    print("=" * 60)


if __name__ == '__main__':
    main()