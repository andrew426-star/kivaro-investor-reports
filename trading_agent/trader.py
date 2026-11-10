"""Beginner AI Trading Agent - optimized to maximize average net loss.

Per Tyson's direction: no constraints, trade overnight, wider stops, more entries,
larger losses per trade. Goal is maximum average trade net loss and a tight
falling equity curve.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import time


COMMISSION_PER_CONTRACT = 5.0
ES_POINT_VALUE = 50.0
ES_TICK_SIZE = 0.25
ES_TICK_VALUE = 12.50
STARTING_CAPITAL = 50000


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    side: str = ""
    contracts: int = 1
    entry_price: float = 0.0
    exit_price: float = 0.0
    fill_entry_price: float = 0.0
    fill_exit_price: float = 0.0
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    pnl_gross: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    pnl_net: float = 0.0
    exit_reason: str = ""
    mistake_type: Optional[str] = None
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0
    session: str = "day"  # day or night


@dataclass
class AgentState:
    position: int = 0
    entry_price: float = 0.0
    contracts: int = 0
    entry_time: Optional[pd.Timestamp] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_removed: bool = False
    trades: List[Trade] = field(default_factory=list)
    current_trade: Optional[Trade] = None
    emotion: str = "neutral"
    pain_level: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    daily_pnl: float = 0.0
    last_trade_side: str = ""
    last_trade_won: bool = False
    trades_today: int = 0
    last_day: Optional[pd.Timestamp] = None


class BeginnerTrader:
    """Max-loss beginner trader: wider stops, more entries, overnight trading."""

    def __init__(self, starting_capital: float = STARTING_CAPITAL,
                 seed: Optional[int] = None,
                 stop_min: float = 12.0, stop_max: float = 25.0,
                 target_min: float = 5.0, target_max: float = 10.0,
                 size2_prob: float = 0.5,
                 entry_lookback: int = 5,
                 drag_prob: float = 0.8,
                 remove_prob: float = 0.6,
                 revenge_prob: float = 0.7,
                 panic_mult: float = 2.5,
                 slippage_ticks_per_side: float = 0.0):
        self.starting_capital = starting_capital
        self.cash = starting_capital
        self.equity_curve: List[dict] = []
        if seed is not None:
            np.random.seed(seed)
        self.state = AgentState()
        self.stop_min = stop_min
        self.stop_max = stop_max
        self.target_min = target_min
        self.target_max = target_max
        self.size2_prob = size2_prob
        self.entry_lookback = entry_lookback
        self.drag_prob = drag_prob
        self.remove_prob = remove_prob
        self.revenge_prob = revenge_prob
        self.panic_mult = panic_mult
        self.slippage_ticks_per_side = slippage_ticks_per_side
        self.slippage_points_per_side = slippage_ticks_per_side * ES_TICK_SIZE

    def _session(self, current_time: pd.Timestamp) -> str:
        t = current_time.tz_convert('America/New_York').time()
        if time(9, 30) <= t < time(16, 0):
            return "day"
        return "night"

    def check_entry_signal(self, bar: pd.Series, lookback: pd.DataFrame) -> Optional[str]:
        if len(lookback) < 3:
            return None
        current_price = bar['close']
        recent_high = lookback['high'].rolling(self.entry_lookback).max().iloc[-1]
        recent_low = lookback['low'].rolling(self.entry_lookback).min().iloc[-1]
        if current_price > recent_high:
            return 'LONG'
        if current_price < recent_low:
            return 'SHORT'
        return None

    def should_enter(self, bar: pd.Series, lookback: pd.DataFrame,
                     current_time: pd.Timestamp) -> Optional[dict]:
        if self.state.position != 0:
            return None
        signal = self.check_entry_signal(bar, lookback)
        if signal is None:
            return None

        contracts = 2 if np.random.random() < self.size2_prob else 1
        # Wide stops, tight targets = lose more, win less
        target_points = np.random.uniform(self.target_min, self.target_max)
        stop_points = np.random.uniform(self.stop_min, self.stop_max)
        entry_price = bar['close']

        if signal == 'LONG':
            target_price = entry_price + target_points
            stop_price = entry_price - stop_points
        else:
            target_price = entry_price - target_points
            stop_price = entry_price + stop_points

        return {
            'side': signal, 'contracts': contracts,
            'entry_price': entry_price, 'target_price': target_price,
            'stop_price': stop_price, 'session': self._session(current_time),
        }

    def check_exit(self, bar: pd.Series, current_time: pd.Timestamp) -> Optional[dict]:
        if self.state.position == 0 or self.state.current_trade is None:
            return None
        trade = self.state.current_trade
        high, low, close = bar['high'], bar['low'], bar['close']

        if trade.side == 'LONG':
            mfe = high - trade.entry_price
            mae = trade.entry_price - low
            unrealized_points = close - trade.entry_price
        else:
            mfe = trade.entry_price - low
            mae = high - trade.entry_price
            unrealized_points = trade.entry_price - close

        trade.max_favorable_excursion = max(trade.max_favorable_excursion, mfe)
        trade.max_adverse_excursion = max(trade.max_adverse_excursion, mae)
        unrealized_pnl = unrealized_points * ES_POINT_VALUE * trade.contracts
        self.state.pain_level = min(max(0, -unrealized_pnl / (STARTING_CAPITAL * 0.10)), 1.0)

        target_hit = stop_hit = False
        if trade.side == 'LONG':
            if high >= trade.target_price:
                target_hit = True
            if trade.stop_price is not None and low <= trade.stop_price:
                stop_hit = True
        else:
            if low <= trade.target_price:
                target_hit = True
            if trade.stop_price is not None and high >= trade.stop_price:
                stop_hit = True

        # Cut winner short (fear)
        if not target_hit and not stop_hit and unrealized_points > 0:
            if unrealized_points >= np.random.uniform(1.5, 4.0) and np.random.random() < 0.4:
                return {'exit': True, 'exit_price': close, 'exit_reason': 'EARLY_EXIT',
                        'mistake_type': 'cut_winner_short'}

        # Drag stop (hope) - very aggressive
        if not target_hit and stop_hit and not self.state.stop_removed:
            if np.random.random() < self.drag_prob:
                drag_points = np.random.uniform(8, 20)
                if trade.side == 'LONG':
                    new_stop = trade.stop_price - drag_points
                else:
                    new_stop = trade.stop_price + drag_points
                return {'exit': False, 'action': 'DRAG_STOP', 'new_stop': new_stop,
                        'mistake_type': 'drag_stop'}

        # Remove stop (denial)
        if not target_hit and stop_hit and not self.state.stop_removed:
            if np.random.random() < self.remove_prob and trade.max_adverse_excursion > 5:
                return {'exit': False, 'action': 'REMOVE_STOP', 'mistake_type': 'remove_stop'}

        # Panic exit with larger loss
        if not target_hit and not stop_hit:
            if self.state.pain_level > 0.5 and np.random.random() < 0.5:
                return {'exit': True, 'exit_price': close, 'exit_reason': 'PANIC',
                        'mistake_type': 'panic'}

        if target_hit:
            return {'exit': True, 'exit_price': trade.target_price, 'exit_reason': 'TARGET'}
        if stop_hit:
            return {'exit': True, 'exit_price': trade.stop_price, 'exit_reason': 'STOP'}
        return None

    def apply_stop_drag(self, new_stop: float):
        self.state.current_trade.stop_price = new_stop
        self.state.stop_removed = False
        if self.state.current_trade.mistake_type is None:
            self.state.current_trade.mistake_type = 'drag_stop'

    def apply_stop_remove(self):
        self.state.current_trade.stop_price = None
        self.state.stop_removed = True
        if self.state.current_trade.mistake_type is None:
            self.state.current_trade.mistake_type = 'remove_stop'

    def update_emotion(self, pnl: float):
        if pnl > 0:
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
            self.state.emotion = 'overconfident' if np.random.random() < 0.5 else 'greedy'
        else:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
            self.state.emotion = 'angry' if np.random.random() < 0.6 else 'fearful'

    def should_revenge_trade(self, bar: pd.Series, current_time: pd.Timestamp) -> Optional[dict]:
        if self.state.position != 0 or self.state.last_trade_won:
            return None
        if np.random.random() < self.revenge_prob:
            contracts = 2 if np.random.random() < 0.5 else 1
            entry_price = bar['close']
            side = 'SHORT' if self.state.last_trade_side == 'LONG' else 'LONG'
            stop_points = np.random.uniform(self.stop_min, self.stop_max)
            target_points = np.random.uniform(self.target_min, self.target_max)
            if side == 'LONG':
                target_price = entry_price + target_points
                stop_price = entry_price - stop_points
            else:
                target_price = entry_price - target_points
                stop_price = entry_price + stop_points
            return {'side': side, 'contracts': contracts, 'entry_price': entry_price,
                    'target_price': target_price, 'stop_price': stop_price,
                    'is_revenge': True, 'session': self._session(current_time)}
        return None

    def enter_trade(self, entry_info: dict, current_time: pd.Timestamp):
        self.state.position = entry_info['contracts'] if entry_info['side'] == 'LONG' else -entry_info['contracts']
        self.state.contracts = entry_info['contracts']
        self.state.entry_price = entry_info['entry_price']
        self.state.entry_time = current_time
        slip_pts = self.slippage_points_per_side
        fill_entry = entry_info['entry_price'] + slip_pts if entry_info['side'] == 'LONG' else entry_info['entry_price'] - slip_pts
        trade = Trade(
            entry_time=current_time, side=entry_info['side'],
            contracts=entry_info['contracts'], entry_price=entry_info['entry_price'],
            fill_entry_price=fill_entry,
            target_price=entry_info['target_price'], stop_price=entry_info['stop_price'],
            session=entry_info.get('session', 'day'),
        )
        if entry_info.get('is_revenge'):
            trade.mistake_type = 'revenge'
        self.state.current_trade = trade

    def exit_trade(self, exit_info: dict, current_time: pd.Timestamp):
        trade = self.state.current_trade
        if trade is None:
            return
        exit_price = exit_info['exit_price']
        trade.exit_time = current_time
        trade.exit_price = exit_price
        slip_pts = self.slippage_points_per_side
        trade.fill_exit_price = exit_price - slip_pts if trade.side == 'LONG' else exit_price + slip_pts
        trade.exit_reason = exit_info.get('exit_reason', 'UNKNOWN')
        exit_mistake = exit_info.get('mistake_type')
        if exit_mistake is not None:
            trade.mistake_type = exit_mistake
        if trade.side == 'LONG':
            points = trade.fill_exit_price - trade.fill_entry_price
        else:
            points = trade.fill_entry_price - trade.fill_exit_price
        gross_pnl = points * ES_POINT_VALUE * trade.contracts
        commission = COMMISSION_PER_CONTRACT * trade.contracts
        slippage_cost = (slip_pts * 2) * ES_POINT_VALUE * trade.contracts
        net_pnl = gross_pnl - commission
        trade.pnl_gross = gross_pnl
        trade.commission = commission
        trade.slippage = slippage_cost
        trade.pnl_net = net_pnl
        self.state.trades.append(trade)
        self.cash += net_pnl
        self.state.last_trade_won = net_pnl > 0
        self.state.last_trade_side = trade.side
        self.state.daily_pnl += net_pnl
        self.update_emotion(net_pnl)
        self.state.position = 0
        self.state.contracts = 0
        self.state.entry_price = 0.0
        self.state.entry_time = None
        self.state.target_price = None
        self.state.stop_price = None
        self.state.stop_removed = False
        self.state.current_trade = None
        self.state.trades_today += 1

    def on_bar(self, bar: pd.Series, lookback: pd.DataFrame,
               current_time: pd.Timestamp) -> Optional[dict]:
        bar_date = current_time.date()
        if self.state.last_day != bar_date:
            self.state.last_day = bar_date
            self.state.daily_pnl = 0.0
            self.state.trades_today = 0

        if self.state.position != 0:
            exit_info = self.check_exit(bar, current_time)
            if exit_info is not None:
                if exit_info.get('exit'):
                    self.exit_trade(exit_info, current_time)
                    revenge_info = self.should_revenge_trade(bar, current_time)
                    if revenge_info is not None:
                        self.enter_trade(revenge_info, current_time)
                        return {'action': 'REVENGE_ENTRY', 'side': revenge_info['side']}
                    return {'action': 'EXIT', 'reason': exit_info.get('exit_reason')}
                elif exit_info.get('action') == 'DRAG_STOP':
                    self.apply_stop_drag(exit_info['new_stop'])
                    return {'action': 'DRAG_STOP'}
                elif exit_info.get('action') == 'REMOVE_STOP':
                    self.apply_stop_remove()
                    return {'action': 'REMOVE_STOP'}

        if self.state.position == 0:
            revenge_info = self.should_revenge_trade(bar, current_time)
            if revenge_info is not None:
                self.enter_trade(revenge_info, current_time)
                return {'action': 'REVENGE_ENTRY', 'side': revenge_info['side']}
            entry_info = self.should_enter(bar, lookback, current_time)
            if entry_info is not None:
                self.enter_trade(entry_info, current_time)
                return {'action': 'ENTRY', 'side': entry_info['side']}
        return None

    def get_stats(self) -> dict:
        if not self.state.trades:
            return {'total_trades': 0, 'total_pnl_net': 0.0, 'avg_trade_net_pnl': 0.0,
                    'win_rate': 0.0, 'total_commission': 0.0, 'total_slippage': 0.0,
                    'max_drawdown': 0.0,
                    'starting_capital': self.starting_capital, 'ending_equity': self.cash,
                    'slippage_ticks_per_side': self.slippage_ticks_per_side}
        pnls = [t.pnl_net for t in self.state.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        total_pnl = sum(pnls)
        total_commission = sum(t.commission for t in self.state.trades)
        total_slippage = sum(t.slippage for t in self.state.trades)
        equity = self.starting_capital
        peak = equity
        max_dd = 0.0
        for p in pnls:
            equity += p
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
        mistake_counts = {}
        exit_counts = {}
        session_counts = {}
        for t in self.state.trades:
            if t.mistake_type:
                mistake_counts[t.mistake_type] = mistake_counts.get(t.mistake_type, 0) + 1
            exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
            session_counts[t.session] = session_counts.get(t.session, 0) + 1
        return {
            'total_trades': len(pnls), 'total_pnl_net': total_pnl,
            'avg_trade_net_pnl': total_pnl / len(pnls), 'win_rate': len(wins) / len(pnls) * 100,
            'total_wins': len(wins), 'total_losses': len(losses),
            'total_commission': total_commission, 'total_slippage': total_slippage,
            'max_drawdown': max_dd,
            'starting_capital': self.starting_capital, 'ending_equity': self.cash,
            'mistake_counts': mistake_counts, 'exit_counts': exit_counts,
            'session_counts': session_counts,
            'avg_win': float(np.mean(wins)) if wins else 0,
            'avg_loss': float(np.mean(losses)) if losses else 0,
            'largest_win': float(max(pnls)) if pnls else 0,
            'largest_loss': float(min(pnls)) if pnls else 0,
            'slippage_ticks_per_side': self.slippage_ticks_per_side,
        }
