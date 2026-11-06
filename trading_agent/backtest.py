"""Backtest engine for the BeginnerTrader agent."""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
from trading_agent.trader import BeginnerTrader, Trade


def resample_to_5min(df: pd.DataFrame) -> pd.DataFrame:
    """Resample 1-second data to 5-minute OHLCV bars."""
    df = df.copy()
    df = df.set_index('timestamp')
    
    # Resample to 5-min
    ohlcv = df['close'].resample('5min').ohlc()
    ohlcv['volume'] = df['volume'].resample('5min').sum()
    
    # Drop NaN bars (overnight/weekend gaps)
    ohlcv = ohlcv.dropna(subset=['close'])
    
    ohlcv = ohlcv.reset_index()
    return ohlcv


def run_backtest(df_5min: pd.DataFrame, starting_capital: float = 50000,
                 seed: Optional[int] = None,
                 warmup_bars: int = 20) -> dict:
    """Run a backtest of the BeginnerTrader on 5-min OHLCV data.
    
    Args:
        df_5min: DataFrame with columns [timestamp, open, high, low, close, volume]
        starting_capital: Starting account balance
        seed: Random seed for reproducibility
        warmup_bars: Number of bars to skip at start (for indicator warmup)
    
    Returns:
        Dictionary with stats, equity curve, and trade log
    """
    agent = BeginnerTrader(starting_capital=starting_capital, seed=seed)
    
    equity_curve = []
    trade_log = []
    action_log = []
    
    for i in range(warmup_bars, len(df_5min)):
        bar = df_5min.iloc[i]
        current_time = bar['timestamp']
        
        # Lookback window for entry signals
        lookback = df_5min.iloc[max(0, i - 50):i]
        
        # Process bar through agent
        result = agent.on_bar(bar, lookback, current_time)
        
        if result is not None:
            action_log.append({
                'timestamp': current_time,
                **result
            })
        
        # Record equity after each bar
        equity = agent.cash
        # Add unrealized P/L if in a position
        if agent.state.position != 0 and agent.state.current_trade is not None:
            trade = agent.state.current_trade
            close = bar['close']
            if trade.side == 'LONG':
                unrealized = (close - trade.entry_price) * 50.0 * trade.contracts
            else:
                unrealized = (trade.entry_price - close) * 50.0 * trade.contracts
            equity += unrealized
        
        equity_curve.append({
            'timestamp': current_time,
            'equity': equity,
            'cash': agent.cash,
            'position': agent.state.position,
        })
        
        # Log completed trades
        if agent.state.trades and len(trade_log) < len(agent.state.trades):
            trade_log.append(agent.state.trades[-1])
    
    stats = agent.get_stats()
    
    return {
        'stats': stats,
        'equity_curve': equity_curve,
        'trade_log': trade_log,
        'action_log': action_log,
        'agent': agent,
    }


def run_walk_forward(df_5min: pd.DataFrame, train_start: str, train_end: str,
                     test_start: str, test_end: str,
                     starting_capital: float = 50000,
                     seed: Optional[int] = None) -> dict:
    """Run backtest on train and test periods separately (walk-forward).
    
    The agent is NOT retrained - same parameters for both periods.
    """
    # Filter to date ranges
    df_5min = df_5min.copy()
    df_5min['date'] = df_5min['timestamp'].dt.date
    
    train_mask = (df_5min['timestamp'] >= train_start) & (df_5min['timestamp'] <= train_end)
    test_mask = (df_5min['timestamp'] >= test_start) & (df_5min['timestamp'] <= test_end)
    
    train_df = df_5min[train_mask].copy()
    test_df = df_5min[test_mask].copy()
    
    print(f"Train period: {train_start} to {train_end}")
    print(f"  Bars: {len(train_df)}, Dates: {train_df['date'].nunique()}")
    print(f"Test period: {test_start} to {test_end}")
    print(f"  Bars: {len(test_df)}, Dates: {test_df['date'].nunique()}")
    
    # Run train backtest
    print("\n=== TRAIN BACKTEST ===")
    train_result = run_backtest(train_df, starting_capital=starting_capital, seed=seed)
    
    # Run test backtest (fresh agent, same parameters)
    print("\n=== TEST BACKTEST (forward test, no optimization) ===")
    test_result = run_backtest(test_df, starting_capital=starting_capital, seed=seed)
    
    return {
        'train': train_result,
        'test': test_result,
    }


def compute_daily_pnl(trade_log: List[Trade]) -> List[dict]:
    """Compute daily P/L from trade log."""
    daily = {}
    for t in trade_log:
        if t.exit_time is None:
            continue
        day = t.exit_time.date()
        if day not in daily:
            daily[day] = {'pnl_net': 0.0, 'trades': 0, 'commission': 0.0}
        daily[day]['pnl_net'] += t.pnl_net
        daily[day]['trades'] += 1
        daily[day]['commission'] += t.commission
    
    result = []
    for day, data in sorted(daily.items()):
        result.append({
            'date': day,
            'pnl_net': data['pnl_net'],
            'trades': data['trades'],
            'commission': data['commission'],
        })
    return result


def compute_equity_curve(equity_curve: List[dict]) -> pd.DataFrame:
    """Convert equity curve list to DataFrame."""
    df = pd.DataFrame(equity_curve)
    if len(df) > 0:
        df['date'] = df['timestamp'].dt.date
        df['daily_peak'] = df.groupby('date')['equity'].cummax()
        df['drawdown'] = df['daily_peak'] - df['equity']
    return df


if __name__ == '__main__':
    # Quick test
    df = pd.read_parquet('data/es_front_month.parquet')
    print(f"Data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Resample to 5-min
    df_5min = resample_to_5min(df)
    print(f"\n5-min bars: {len(df_5min)}")
    print(f"5-min date range: {df_5min['timestamp'].min()} to {df_5min['timestamp'].max()}")