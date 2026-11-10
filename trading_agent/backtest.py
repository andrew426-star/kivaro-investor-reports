"""Backtest engine for the BeginnerTrader agent."""
import pandas as pd
import numpy as np
from typing import Optional, List
from trading_agent.trader import BeginnerTrader, Trade


def resample_to_5min(df: pd.DataFrame) -> pd.DataFrame:
    """Resample 1-second data to 5-minute OHLCV bars."""
    df = df.copy()
    df = df.set_index('timestamp')
    ohlcv = df['close'].resample('5min').ohlc()
    ohlcv['volume'] = df['volume'].resample('5min').sum()
    ohlcv = ohlcv.dropna(subset=['close'])
    ohlcv = ohlcv.reset_index()
    return ohlcv


def run_backtest(df_5min: pd.DataFrame, starting_capital: float = 50000,
                 seed: Optional[int] = None,
                 warmup_bars: int = 20,
                 agent_kwargs: Optional[dict] = None) -> dict:
    """Run a backtest of the BeginnerTrader on 5-min OHLCV data."""
    kwargs = agent_kwargs or {}
    agent = BeginnerTrader(starting_capital=starting_capital, seed=seed, **kwargs)
    equity_curve = []
    trade_log = []
    action_log = []

    for i in range(warmup_bars, len(df_5min)):
        bar = df_5min.iloc[i]
        current_time = bar['timestamp']
        lookback = df_5min.iloc[max(0, i - 50):i]
        result = agent.on_bar(bar, lookback, current_time)
        if result is not None:
            action_log.append({'timestamp': current_time, **result})

        equity = agent.cash
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
                     seed: Optional[int] = None,
                     agent_kwargs: Optional[dict] = None) -> dict:
    """Run backtest on train and test periods separately."""
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

    print("\n=== TRAIN BACKTEST ===")
    train_result = run_backtest(train_df, starting_capital=starting_capital, seed=seed, agent_kwargs=agent_kwargs)
    print("\n=== TEST BACKTEST (forward test) ===")
    test_result = run_backtest(test_df, starting_capital=starting_capital, seed=seed, agent_kwargs=agent_kwargs)
    return {'train': train_result, 'test': test_result}


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
    return [{'date': d, **v} for d, v in sorted(daily.items())]


def compute_equity_curve(equity_curve: List[dict]) -> pd.DataFrame:
    """Convert equity curve list to DataFrame."""
    df = pd.DataFrame(equity_curve)
    if len(df) > 0:
        df['date'] = df['timestamp'].dt.date
        df['daily_peak'] = df.groupby('date')['equity'].cummax()
        df['drawdown'] = df['daily_peak'] - df['equity']
    return df