"""Main runner for the BeginnerTrader backtest.

Runs 1.5-year training backtest + 6-month forward test on ES futures data.
Outputs stats required by Serac Investments challenge.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import json
from datetime import datetime

from trading_agent.backtest import (
    resample_to_5min, run_walk_forward, compute_daily_pnl, compute_equity_curve
)


def main():
    print("=" * 60)
    print("Beginner AI Trading Agent - Serac Investments Challenge")
    print("=" * 60)
    
    # Load data
    print("\nLoading ES data...")
    df = pd.read_parquet('data/es_front_month.parquet')
    print(f"  Shape: {df.shape}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Resample to 5-min bars
    print("\nResampling to 5-minute bars...")
    df_5min = resample_to_5min(df)
    print(f"  5-min bars: {len(df_5min)}")
    print(f"  Date range: {df_5min['timestamp'].min()} to {df_5min['timestamp'].max()}")
    
    # Define periods
    # Total data: 2023-10-27 to 2026-10-26 (~3 years)
    # Train: first 1.5 years = 2023-10-27 to 2025-04-27
    # Test: last 6 months = 2026-04-27 to 2026-10-26
    train_start = '2023-10-27'
    train_end = '2025-04-27'
    test_start = '2026-04-27'
    test_end = '2026-10-26'
    
    print(f"\nTrain period: {train_start} to {train_end}")
    print(f"Test period: {test_start} to {test_end}")
    
    # Run walk-forward backtest
    results = run_walk_forward(
        df_5min,
        train_start=train_start,
        train_end=train_end,
        test_start=test_start,
        test_end=test_end,
        starting_capital=50000,
        seed=42,  # reproducible
    )
    
    # Print stats
    print("\n" + "=" * 60)
    print("TRAIN BACKTEST RESULTS (1.5 years)")
    print("=" * 60)
    print_stats(results['train']['stats'], "Train")
    
    print("\n" + "=" * 60)
    print("FORWARD TEST RESULTS (last 6 months, no optimization)")
    print("=" * 60)
    print_stats(results['test']['stats'], "Test")
    
    # Daily P/L for test period
    print("\n" + "=" * 60)
    print("DAILY P/L (Test Period)")
    print("=" * 60)
    daily = compute_daily_pnl(results['test']['trade_log'])
    if daily:
        daily_df = pd.DataFrame(daily)
        print(daily_df.to_string(index=False))
        print(f"\n  Days with trades: {len(daily_df)}")
        print(f"  Avg daily P/L: ${daily_df['pnl_net'].mean():.2f}")
        print(f"  Std daily P/L: ${daily_df['pnl_net'].std():.2f}")
        print(f"  Best day: ${daily_df['pnl_net'].max():.2f}")
        print(f"  Worst day: ${daily_df['pnl_net'].min():.2f}")
    
    # Equity curve
    equity_df = compute_equity_curve(results['test']['equity_curve'])
    if len(equity_df) > 0:
        print(f"\n  Peak equity: ${equity_df['equity'].max():.2f}")
        print(f"  Valley equity: ${equity_df['equity'].min():.2f}")
        print(f"  Max drawdown: ${equity_df['drawdown'].max():.2f}")
    
    # Trade log summary
    print("\n" + "=" * 60)
    print("TRADE LOG (Test Period - first 20 trades)")
    print("=" * 60)
    trade_log = results['test']['trade_log']
    for i, t in enumerate(trade_log[:20]):
        print(f"  #{i+1}: {t.entry_time} {t.side} {t.contracts}c @ {t.entry_price:.2f} -> "
              f"{t.exit_price:.2f} | P/L: ${t.pnl_net:.2f} | {t.exit_reason} | "
              f"mistake: {t.mistake_type or '-'} | MAE: {t.max_adverse_excursion:.1f}pts | "
              f"MFE: {t.max_favorable_excursion:.1f}pts")
    
    if len(trade_log) > 20:
        print(f"  ... and {len(trade_log) - 20} more trades")
    
    # Save results
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)
    
    # Save stats as JSON
    all_stats = {
        'train': results['train']['stats'],
        'test': results['test']['stats'],
        'daily_pnl_test': daily,
        'metadata': {
            'starting_capital': 50000,
            'commission_per_contract': 5.0,
            'es_point_value': 50.0,
            'train_period': f"{train_start} to {train_end}",
            'test_period': f"{test_start} to {test_end}",
            'seed': 42,
        },
    }
    
    with open(output_dir / 'stats.json', 'w') as f:
        json.dump(all_stats, f, indent=2, default=str)
    print(f"\nSaved stats to {output_dir / 'stats.json'}")
    
    # Save equity curve
    equity_df.to_parquet(output_dir / 'equity_curve_test.parquet', index=False)
    print(f"Saved equity curve to {output_dir / 'equity_curve_test.parquet'}")
    
    # Save trade log
    trade_rows = []
    for t in trade_log:
        trade_rows.append({
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'side': t.side,
            'contracts': t.contracts,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'target_price': t.target_price,
            'stop_price': t.stop_price,
            'pnl_gross': t.pnl_gross,
            'commission': t.commission,
            'pnl_net': t.pnl_net,
            'exit_reason': t.exit_reason,
            'mistake_type': t.mistake_type,
            'max_adverse_excursion': t.max_adverse_excursion,
            'max_favorable_excursion': t.max_favorable_excursion,
        })
    trade_df = pd.DataFrame(trade_rows)
    trade_df.to_parquet(output_dir / 'trade_log_test.parquet', index=False)
    print(f"Saved trade log to {output_dir / 'trade_log_test.parquet'}")
    
    print("\n" + "=" * 60)
    print("BACKTEST COMPLETE")
    print("=" * 60)


def print_stats(stats: dict, label: str):
    """Print trading statistics."""
    print(f"  Total trades: {stats['total_trades']}")
    print(f"  Total net P/L: ${stats['total_pnl_net']:.2f}")
    print(f"  Average trade net P/L: ${stats['avg_trade_net_pnl']:.2f}")
    print(f"  Win rate: {stats['win_rate']:.1f}%")
    print(f"  Total wins: {stats['total_wins']}")
    print(f"  Total losses: {stats['total_losses']}")
    print(f"  Total commission: ${stats['total_commission']:.2f}")
    print(f"  Max drawdown: ${stats['max_drawdown']:.2f}")
    print(f"  Starting capital: ${stats['starting_capital']:.2f}")
    print(f"  Ending equity: ${stats['ending_equity']:.2f}")
    print(f"  Avg win: ${stats['avg_win']:.2f}")
    print(f"  Avg loss: ${stats['avg_loss']:.2f}")
    print(f"  Largest win: ${stats['largest_win']:.2f}")
    print(f"  Largest loss: ${stats['largest_loss']:.2f}")
    if stats.get('mistake_counts'):
        print(f"  Mistakes: {stats['mistake_counts']}")
    if stats.get('exit_counts'):
        print(f"  Exit reasons: {stats['exit_counts']}")


if __name__ == '__main__':
    main()