"""Stress test the BeginnerTrader with 5 different random seeds."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import json

from trading_agent.backtest import (
    resample_to_5min, run_walk_forward, compute_daily_pnl, compute_equity_curve
)


def main():
    print("=" * 60)
    print("STRESS TEST: BeginnerTrader with 5 different seeds")
    print("=" * 60)
    
    # Load data
    df = pd.read_parquet('data/es_front_month.parquet')
    df_5min = resample_to_5min(df)
    
    # Forward test period (last 6 months)
    test_start = '2026-04-27'
    test_end = '2026-10-26'
    
    seeds = [42, 123, 456, 789, 999]
    results = []
    
    for seed in seeds:
        print(f"\n--- Seed {seed} ---")
        # Run forward test only (no training optimization)
        test_mask = (df_5min['timestamp'] >= test_start) & (df_5min['timestamp'] <= test_end)
        test_df = df_5min[test_mask].copy()
        
        from trading_agent.backtest import run_backtest
        result = run_backtest(test_df, starting_capital=50000, seed=seed)
        stats = result['stats']
        
        # Compute drawdown from equity curve
        equity_df = compute_equity_curve(result['equity_curve'])
        max_dd = equity_df['drawdown'].max() if len(equity_df) > 0 else 0
        peak_equity = equity_df['equity'].max() if len(equity_df) > 0 else stats['ending_equity']
        valley_equity = equity_df['equity'].min() if len(equity_df) > 0 else stats['ending_equity']
        
        daily = compute_daily_pnl(result['trade_log'])
        daily_df = pd.DataFrame(daily) if daily else pd.DataFrame()
        
        result_summary = {
            'seed': seed,
            'total_trades': stats['total_trades'],
            'total_pnl_net': stats['total_pnl_net'],
            'avg_trade_net_pnl': stats['avg_trade_net_pnl'],
            'win_rate': stats['win_rate'],
            'max_drawdown': max_dd,
            'ending_equity': stats['ending_equity'],
            'total_commission': stats['total_commission'],
            'peak_equity': peak_equity,
            'valley_equity': valley_equity,
            'avg_daily_pnl': daily_df['pnl_net'].mean() if len(daily_df) > 0 else 0,
            'worst_day': daily_df['pnl_net'].min() if len(daily_df) > 0 else 0,
            'best_day': daily_df['pnl_net'].max() if len(daily_df) > 0 else 0,
            'mistake_counts': stats.get('mistake_counts', {}),
            'exit_counts': stats.get('exit_counts', {}),
        }
        results.append(result_summary)
        
        print(f"  Trades: {stats['total_trades']}")
        print(f"  Net P/L: ${stats['total_pnl_net']:.2f}")
        print(f"  Avg Trade: ${stats['avg_trade_net_pnl']:.2f}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Max Drawdown: ${max_dd:.2f}")
        print(f"  Ending Equity: ${stats['ending_equity']:.2f}")
        print(f"  Mistakes: {stats.get('mistake_counts', {})}")
    
    # Summary across all seeds
    print("\n" + "=" * 60)
    print("STRESS TEST SUMMARY (5 seeds, same forward test period)")
    print("=" * 60)
    
    df_results = pd.DataFrame(results)
    print(f"\nAverage Trade Net P/L: ${df_results['avg_trade_net_pnl'].mean():.2f} "
          f"(std: ${df_results['avg_trade_net_pnl'].std():.2f})")
    print(f"Average Win Rate: {df_results['win_rate'].mean():.1f}% "
          f"(std: {df_results['win_rate'].std():.1f}%)")
    print(f"Average Total P/L: ${df_results['total_pnl_net'].mean():.2f} "
          f"(std: ${df_results['total_pnl_net'].std():.2f})")
    print(f"Average Max Drawdown: ${df_results['max_drawdown'].mean():.2f} "
          f"(std: ${df_results['max_drawdown'].std():.2f})")
    print(f"Average Ending Equity: ${df_results['ending_equity'].mean():.2f} "
          f"(std: ${df_results['ending_equity'].std():.2f})")
    print(f"All seeds lost money: {(df_results['total_pnl_net'] < 0).all()}")
    print(f"All seeds had max drawdown > $0: {(df_results['max_drawdown'] > 0).all()}")
    
    # Mistake consistency
    all_mistakes = {}
    for r in results:
        for k, v in r['mistake_counts'].items():
            all_mistakes[k] = all_mistakes.get(k, 0) + v
    print(f"\nTotal mistakes across 5 seeds: {all_mistakes}")
    
    # Save stress test results
    output_dir = Path('results')
    output_dir.mkdir(exist_ok=True)
    
    stress_results = {
        'seeds': seeds,
        'test_period': f"{test_start} to {test_end}",
        'individual_results': results,
        'summary': {
            'avg_trade_net_pnl': float(df_results['avg_trade_net_pnl'].mean()),
            'std_trade_net_pnl': float(df_results['avg_trade_net_pnl'].std()),
            'avg_win_rate': float(df_results['win_rate'].mean()),
            'std_win_rate': float(df_results['win_rate'].std()),
            'avg_total_pnl': float(df_results['total_pnl_net'].mean()),
            'std_total_pnl': float(df_results['total_pnl_net'].std()),
            'avg_max_drawdown': float(df_results['max_drawdown'].mean()),
            'std_max_drawdown': float(df_results['max_drawdown'].std()),
            'avg_ending_equity': float(df_results['ending_equity'].mean()),
            'std_ending_equity': float(df_results['ending_equity'].std()),
            'all_lost_money': bool((df_results['total_pnl_net'] < 0).all()),
            'total_mistakes': all_mistakes,
        },
    }
    
    with open(output_dir / 'stress_test_results.json', 'w') as f:
        json.dump(stress_results, f, indent=2, default=str)
    print(f"\nSaved stress test results to {output_dir / 'stress_test_results.json'}")
    
    print("\n" + "=" * 60)
    print("STRESS TEST COMPLETE - Agent is ready for Serac")
    print("=" * 60)


if __name__ == '__main__':
    main()