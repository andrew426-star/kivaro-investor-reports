"""Beginner AI Trading Agent - trades like an inexperienced day trader.

This agent simulates the mistakes, emotions, and poor decisions of a beginner
day trader trading ES futures. The goal is NOT profitability - it's realistic
beginner behavior that leads to losses.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import time, timedelta


# ============================================================
# Configuration
# ============================================================

COMMISSION_PER_CONTRACT = 5.0  # $5 round turn per contract
ES_POINT_VALUE = 50.0  # $50 per ES point per contract

CONTRACT_MIN = 1
CONTRACT_MAX = 2
TARGET_MIN_POINTS = 7
TARGET_MAX_POINTS = 12
STOP_MIN_POINTS = 7
STOP_MAX_POINTS = 12

STARTING_CAPITAL = 50000  # $50k starting account (realistic for a beginner)


@dataclass
class Trade:
    """Record of a single trade."""
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    side: str = ""  # 'LONG' or 'SHORT'
    contracts: int = 1
    entry_price: float = 0.0
    exit_price: float = 0.0
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    pnl_gross: float = 0.0
    commission: float = 0.0
    pnl_net: float = 0.0
    exit_reason: str = ""  # TARGET, STOP, EARLY_EXIT, STOP_DRAG, STOP_REMOVE, PANIC, REVENGE, EOD
    mistake_type: Optional[str] = None  # 'cut_winner_short', 'drag_stop', 'remove_stop', 'panic', 'revenge', 'overconfident'
    max_adverse_excursion: float = 0.0
    max_favorable_excursion: float = 0.0


@dataclass
class AgentState:
    """Current state of the trading agent."""
    position: int = 0  # -2 to 2
    entry_price: float = 0.0
    contracts: int = 0
    entry_time: Optional[pd.Timestamp] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    stop_original: Optional[float] = None  # original stop before dragging
    stop_removed: bool = False
    target_hit: bool = False
    stop_hit: bool = False
    trades: List[Trade] = field(default_factory=list)
    current_trade: Optional[Trade] = None
    
    # Emotion/Pain state
    emotion: str = "neutral"  # neutral, fearful, angry, greedy, overconfident, panicked
    pain_level: float = 0.0  # 0-1, based on unrealized P/L
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    daily_loss: float = 0.0  # today's realized P/L
    daily_pnl: float = 0.0
    
    # Memory
    last_trade_side: str = ""
    last_trade_won: bool = False
    trades_today: int = 0
    last_day: Optional[pd.Timestamp] = None


class BeginnerTrader:
    """AI trading agent that trades like an inexperienced day trader."""
    
    def __init__(self, starting_capital: float = STARTING_CAPITAL,
                 seed: Optional[int] = None):
        self.starting_capital = starting_capital
        self.cash = starting_capital
        self.equity_curve: List[dict] = []
        
        if seed is not None:
            np.random.seed(seed)
        
        self.state = AgentState()
        self.daily_stats: List[dict] = []
        self.current_date = None
    
    # ----------------------------------------------------------
    # Entry logic - simple and consistent
    # ----------------------------------------------------------
    def check_entry_signal(self, bar: pd.Series, lookback: pd.DataFrame) -> Optional[str]:
        """Check if there's an entry signal.
        
        Simple logic: price breakout above recent high = LONG,
        price breakdown below recent low = SHORT.
        This is consistent and simple - exactly what a beginner might use.
        """
        if len(lookback) < 5:
            return None
        
        current_price = bar['close']
        recent_high = lookback['high'].rolling(10).max().iloc[-1]
        recent_low = lookback['low'].rolling(10).min().iloc[-1]
        
        # Long signal: breakout above recent high
        if current_price > recent_high:
            return 'LONG'
        # Short signal: breakdown below recent low
        if current_price < recent_low:
            return 'SHORT'
        
        return None
    
    def should_enter(self, bar: pd.Series, lookback: pd.DataFrame,
                     current_time: pd.Timestamp) -> Optional[dict]:
        """Decide whether to enter a trade and with what parameters."""
        # Only enter during trading hours (09:30 - 15:30 ET, stop new entries after 15:30)
        t = current_time.tz_convert('America/New_York').time()
        if t >= time(15, 30):
            return None
        
        # Max 2 contracts
        if self.state.position != 0:
            return None
        
        signal = self.check_entry_signal(bar, lookback)
        if signal is None:
            return None
        
        # Position sizing: usually 1, sometimes 2 if overconfident
        contracts = 1
        if self.state.emotion == 'overconfident':
            # Overconfident traders size up - 2 contracts 70% of the time
            contracts = 2 if np.random.random() < 0.7 else 1
        elif np.random.random() < 0.15:
            contracts = 2
        
        # Target and stop: 7-12 points normally, wider when overconfident
        if self.state.emotion == 'overconfident':
            target_points = np.random.uniform(10, 18)  # greedy targets
            stop_points = np.random.uniform(10, 20)    # wide stops (overconfident)
        else:
            target_points = np.random.uniform(TARGET_MIN_POINTS, TARGET_MAX_POINTS)
            stop_points = np.random.uniform(STOP_MIN_POINTS, STOP_MAX_POINTS)
        
        entry_price = bar['close']
        
        if signal == 'LONG':
            target_price = entry_price + target_points
            stop_price = entry_price - stop_points
        else:  # SHORT
            target_price = entry_price - target_points
            stop_price = entry_price + stop_points
        
        return {
            'side': signal,
            'contracts': contracts,
            'entry_price': entry_price,
            'target_price': target_price,
            'stop_price': stop_price,
            'target_points': target_points,
            'stop_points': stop_points,
        }
    
    # ----------------------------------------------------------
    # Exit logic - where the beginner makes mistakes
    # ----------------------------------------------------------
    def check_exit(self, bar: pd.Series, current_time: pd.Timestamp) -> Optional[dict]:
        """Check if the current position should be exited.
        
        This is where beginner behavior shows up:
        - Normal: hit target or stop
        - Mistake: cut winners short (fear)
        - Mistake: drag stops (hope)
        - Mistake: remove stops (denial)
        - Mistake: panic exit (too much pain)
        - Mistake: revenge trade entry after loss
        - EOD: flat at end of day
        """
        if self.state.position == 0 or self.state.current_trade is None:
            return None
        
        trade = self.state.current_trade
        high = bar['high']
        low = bar['low']
        close = bar['close']
        
        # Update MFE/MAE
        if trade.side == 'LONG':
            mfe = high - trade.entry_price
            mae = trade.entry_price - low
        else:
            mfe = trade.entry_price - low
            mae = high - trade.entry_price
        
        trade.max_favorable_excursion = max(trade.max_favorable_excursion, mfe)
        trade.max_adverse_excursion = max(trade.max_adverse_excursion, mae)
        
        # Calculate unrealized P/L in points
        if trade.side == 'LONG':
            unrealized_points = close - trade.entry_price
        else:
            unrealized_points = trade.entry_price - close
        
        unrealized_pnl = unrealized_points * ES_POINT_VALUE * trade.contracts
        
        # Update pain level
        self.state.pain_level = max(0, -unrealized_pnl / (STARTING_CAPITAL * 0.10))
        self.state.pain_level = min(self.state.pain_level, 1.0)
        
        # ------------------------------------------------------
        # 1. NORMAL EXITS: target or stop hit
        # ------------------------------------------------------
        target_hit = False
        stop_hit = False
        
        if trade.side == 'LONG':
            if high >= trade.target_price:
                target_hit = True
            if trade.stop_price is not None and low <= trade.stop_price:
                stop_hit = True
        else:  # SHORT
            if low <= trade.target_price:
                target_hit = True
            if trade.stop_price is not None and high >= trade.stop_price:
                stop_hit = True
        
        # ------------------------------------------------------
        # 2. BEGINNER MISTAKES
        # ------------------------------------------------------
        
        # Mistake: Cut winner short (fear) - exit early with small profit
        if not target_hit and not stop_hit and unrealized_points > 0:
            # Fear: exit winner early if profit is small but positive
            fear_threshold = np.random.uniform(2.0, 5.0)  # points
            if (unrealized_points >= fear_threshold and 
                self.state.emotion == 'fearful' and 
                np.random.random() < 0.3):
                return {
                    'exit': True,
                    'exit_price': close,
                    'exit_reason': 'EARLY_EXIT',
                    'mistake_type': 'cut_winner_short',
                }
        
        # Mistake: Drag stop (hope) - when stop is about to be hit, move it further
        if not target_hit and stop_hit and not self.state.stop_removed:
            # Beginners often drag stops when in pain - higher probability
            if (self.state.emotion in ('fearful', 'neutral', 'angry') and 
                np.random.random() < 0.6):
                # Drag the stop further away by 5-15 points
                drag_points = np.random.uniform(5, 15)
                if trade.side == 'LONG':
                    new_stop = trade.stop_price - drag_points
                else:
                    new_stop = trade.stop_price + drag_points
                
                return {
                    'exit': False,
                    'action': 'DRAG_STOP',
                    'new_stop': new_stop,
                    'mistake_type': 'drag_stop',
                }
        
        # Mistake: Remove stop entirely (denial) - when stop is hit, remove it and hope
        if not target_hit and stop_hit and not self.state.stop_removed:
            if (self.state.emotion in ('fearful', 'angry', 'overconfident') and 
                np.random.random() < 0.35 and
                trade.max_adverse_excursion > 8):
                return {
                    'exit': False,
                    'action': 'REMOVE_STOP',
                    'mistake_type': 'remove_stop',
                }
        
        # Mistake: Panic exit when pain is too high
        if not target_hit and not stop_hit:
            # Pain-based panic exit - exit with 2-3x planned loss
            if self.state.pain_level > 0.7 and np.random.random() < 0.4:
                return {
                    'exit': True,
                    'exit_price': close,
                    'exit_reason': 'PANIC',
                    'mistake_type': 'panic',
                }
        
        # Mistake: Exit at end of day
        t = current_time.tz_convert('America/New_York').time()
        if t >= time(16, 0):
            return {
                'exit': True,
                'exit_price': close,
                'exit_reason': 'EOD',
            }
        
        # Normal target/stop exits
        if target_hit:
            return {
                'exit': True,
                'exit_price': trade.target_price,
                'exit_reason': 'TARGET',
            }
        
        if stop_hit:
            # Overconfident traders hold losers - ignore the stop sometimes
            if (self.state.emotion == 'overconfident' and 
                np.random.random() < 0.4 and
                not self.state.stop_removed):
                # Hold and hope - don't exit, widen the stop instead
                drag_points = np.random.uniform(10, 20)
                if trade.side == 'LONG':
                    new_stop = trade.stop_price - drag_points
                else:
                    new_stop = trade.stop_price + drag_points
                return {
                    'exit': False,
                    'action': 'DRAG_STOP',
                    'new_stop': new_stop,
                    'mistake_type': 'drag_stop',
                }
            return {
                'exit': True,
                'exit_price': trade.stop_price,
                'exit_reason': 'STOP',
            }
        
        return None
    
    def apply_stop_drag(self, new_stop: float):
        """Apply a dragged stop to the current position."""
        self.state.current_trade.stop_price = new_stop
        self.state.stop_removed = False
        self.state.emotion = 'fearful'
        # Track the mistake on the trade
        if self.state.current_trade.mistake_type is None:
            self.state.current_trade.mistake_type = 'drag_stop'
    
    def apply_stop_remove(self):
        """Remove the stop entirely."""
        self.state.current_trade.stop_price = None
        self.state.stop_removed = True
        self.state.emotion = 'angry'
        # Track the mistake on the trade
        if self.state.current_trade.mistake_type is None:
            self.state.current_trade.mistake_type = 'remove_stop'
    
    # ----------------------------------------------------------
    # Emotion state updates
    # ----------------------------------------------------------
    def update_emotion(self, trade_result: Optional[dict] = None):
        """Update emotion state based on recent trades."""
        if trade_result is None:
            return
        
        pnl = trade_result.get('pnl_net', 0)
        
        if pnl > 0:
            self.state.consecutive_wins += 1
            self.state.consecutive_losses = 0
            # Overconfidence after 1+ wins - beginners get overconfident quickly
            if self.state.consecutive_wins >= 1 and np.random.random() < 0.35:
                self.state.emotion = 'overconfident'
            else:
                self.state.emotion = 'greedy'
        else:
            self.state.consecutive_losses += 1
            self.state.consecutive_wins = 0
            # Fear after any loss
            if self.state.consecutive_losses >= 1:
                self.state.emotion = 'fearful'
            # Anger after any loss - revenge trigger
            if np.random.random() < 0.5:
                self.state.emotion = 'angry'
    
    def should_revenge_trade(self, bar: pd.Series, current_time: pd.Timestamp) -> Optional[dict]:
        """After a loss, the beginner may revenge trade - enter opposite direction with no signal."""
        if (self.state.position != 0 or 
            self.state.last_trade_won):
            return None
        
        t = current_time.tz_convert('America/New_York').time()
        if t >= time(15, 30):
            return None
        
        # 50% chance of revenge trading after a loss (beginners revenge trade often)
        if np.random.random() < 0.5:
            contracts = 1
            if self.state.emotion == 'overconfident' or self.state.consecutive_losses >= 2:
                contracts = 2 if np.random.random() < 0.3 else 1
            
            entry_price = bar['close']
            # Opposite direction of last trade
            side = 'SHORT' if self.state.last_trade_side == 'LONG' else 'LONG'
            
            if side == 'LONG':
                target_price = entry_price + np.random.uniform(7, 12)
                stop_price = entry_price - np.random.uniform(7, 12)
            else:
                target_price = entry_price - np.random.uniform(7, 12)
                stop_price = entry_price + np.random.uniform(7, 12)
            
            return {
                'side': side,
                'contracts': contracts,
                'entry_price': entry_price,
                'target_price': target_price,
                'stop_price': stop_price,
                'is_revenge': True,
            }
        
        return None
    
    # ----------------------------------------------------------
    # Trade execution
    # ----------------------------------------------------------
    def enter_trade(self, entry_info: dict, current_time: pd.Timestamp):
        """Enter a new trade."""
        self.state.position = entry_info['contracts'] if entry_info['side'] == 'LONG' else -entry_info['contracts']
        self.state.contracts = entry_info['contracts']
        self.state.entry_price = entry_info['entry_price']
        self.state.entry_time = current_time
        
        trade = Trade(
            entry_time=current_time,
            side=entry_info['side'],
            contracts=entry_info['contracts'],
            entry_price=entry_info['entry_price'],
            target_price=entry_info['target_price'],
            stop_price=entry_info['stop_price'],
        )
        if entry_info.get('is_revenge'):
            trade.mistake_type = 'revenge'
        self.state.current_trade = trade
    
    def exit_trade(self, exit_info: dict, current_time: pd.Timestamp):
        """Exit the current trade."""
        trade = self.state.current_trade
        if trade is None:
            return
        
        exit_price = exit_info['exit_price']
        trade.exit_time = current_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_info.get('exit_reason', 'UNKNOWN')
        # Preserve mistake_type from drag/remove if already set, otherwise use exit_info
        exit_mistake = exit_info.get('mistake_type')
        if exit_mistake is not None:
            trade.mistake_type = exit_mistake
        
        # Calculate P/L
        if trade.side == 'LONG':
            points = exit_price - trade.entry_price
        else:
            points = trade.entry_price - exit_price
        
        gross_pnl = points * ES_POINT_VALUE * trade.contracts
        commission = COMMISSION_PER_CONTRACT * trade.contracts
        net_pnl = gross_pnl - commission
        
        trade.pnl_gross = gross_pnl
        trade.commission = commission
        trade.pnl_net = net_pnl
        
        self.state.trades.append(trade)
        
        # Update cash
        self.cash += net_pnl
        
        # Update emotion tracking
        won = net_pnl > 0
        self.state.last_trade_won = won
        self.state.last_trade_side = trade.side
        self.state.daily_pnl += net_pnl
        
        self.update_emotion({'pnl_net': net_pnl})
        
        # Reset position
        self.state.position = 0
        self.state.contracts = 0
        self.state.entry_price = 0.0
        self.state.entry_time = None
        self.state.target_price = None
        self.state.stop_price = None
        self.state.stop_original = None
        self.state.stop_removed = False
        self.state.current_trade = None
        self.state.trades_today += 1
    
    # ----------------------------------------------------------
    # Main bar processing
    # ----------------------------------------------------------
    def on_bar(self, bar: pd.Series, lookback: pd.DataFrame,
               current_time: pd.Timestamp) -> Optional[dict]:
        """Process a single bar. Returns action taken or None."""
        # Check date change (reset daily stats)
        bar_date = current_time.date()
        if self.current_date != bar_date:
            self.current_date = bar_date
            self.state.daily_pnl = 0.0
            self.state.trades_today = 0
            self.state.last_day = pd.Timestamp(bar_date)
        
        # If we have a position, check for exit first
        if self.state.position != 0:
            exit_info = self.check_exit(bar, current_time)
            
            if exit_info is not None:
                if exit_info.get('exit'):
                    self.exit_trade(exit_info, current_time)
                    
                    # After exiting, check for revenge trade
                    revenge_info = self.should_revenge_trade(bar, current_time)
                    if revenge_info is not None:
                        self.enter_trade(revenge_info, current_time)
                        return {'action': 'REVENGE_ENTRY', 'side': revenge_info['side'],
                                'contracts': revenge_info['contracts']}
                    
                    return {'action': 'EXIT', 'reason': exit_info.get('exit_reason'),
                            'mistake': exit_info.get('mistake_type')}
                
                elif exit_info.get('action') == 'DRAG_STOP':
                    self.apply_stop_drag(exit_info['new_stop'])
                    return {'action': 'DRAG_STOP', 'new_stop': exit_info['new_stop'],
                            'mistake': 'drag_stop'}
                
                elif exit_info.get('action') == 'REMOVE_STOP':
                    self.apply_stop_remove()
                    return {'action': 'REMOVE_STOP', 'mistake': 'remove_stop'}
        
        # No position - check for entry
        if self.state.position == 0:
            # Check revenge trade first (takes priority over signal entry)
            revenge_info = self.should_revenge_trade(bar, current_time)
            if revenge_info is not None:
                self.enter_trade(revenge_info, current_time)
                return {'action': 'REVENGE_ENTRY', 'side': revenge_info['side'],
                        'contracts': revenge_info['contracts']}
            
            # Normal entry signal
            entry_info = self.should_enter(bar, lookback, current_time)
            if entry_info is not None:
                self.enter_trade(entry_info, current_time)
                return {'action': 'ENTRY', 'side': entry_info['side'],
                        'contracts': entry_info['contracts']}
        
        return None
    
    # ----------------------------------------------------------
    # Reporting
    # ----------------------------------------------------------
    def get_stats(self) -> dict:
        """Calculate trading statistics."""
        if not self.state.trades:
            return {
                'total_trades': 0,
                'total_pnl_net': 0.0,
                'avg_trade_net_pnl': 0.0,
                'win_rate': 0.0,
                'total_commission': 0.0,
                'max_drawdown': 0.0,
                'starting_capital': self.starting_capital,
                'ending_equity': self.cash,
            }
        
        pnls = [t.pnl_net for t in self.state.trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_pnl = sum(pnls)
        total_commission = sum(t.commission for t in self.state.trades)
        avg_pnl = total_pnl / len(pnls)
        win_rate = len(wins) / len(pnls) * 100
        
        # Equity curve and max drawdown
        equity = self.starting_capital
        peak = equity
        max_dd = 0.0
        for p in pnls:
            equity += p
            peak = max(peak, equity)
            dd = peak - equity
            max_dd = max(max_dd, dd)
        
        # Mistake breakdown
        mistake_counts = {}
        for t in self.state.trades:
            if t.mistake_type:
                mistake_counts[t.mistake_type] = mistake_counts.get(t.mistake_type, 0) + 1
        
        # Exit reason breakdown
        exit_counts = {}
        for t in self.state.trades:
            exit_counts[t.exit_reason] = exit_counts.get(t.exit_reason, 0) + 1
        
        return {
            'total_trades': len(pnls),
            'total_pnl_net': total_pnl,
            'avg_trade_net_pnl': avg_pnl,
            'win_rate': win_rate,
            'total_wins': len(wins),
            'total_losses': len(losses),
            'total_commission': total_commission,
            'max_drawdown': max_dd,
            'starting_capital': self.starting_capital,
            'ending_equity': self.cash,
            'mistake_counts': mistake_counts,
            'exit_counts': exit_counts,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
            'largest_win': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0,
        }