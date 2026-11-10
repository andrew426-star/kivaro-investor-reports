import pandas as pd
from trading_agent.trader import BeginnerTrader

def test_slippage():
    t = BeginnerTrader(seed=1, slippage_ticks_per_side=1.0)
    now = pd.Timestamp('2026-01-01T14:00:00Z')
    t.enter_trade({'side':'LONG','contracts':1,'entry_price':5000.0,'target_price':5010.0,'stop_price':4990.0,'session':'day'}, now)
    t.exit_trade({'exit_price':5010.0,'exit_reason':'TARGET'}, now + pd.Timedelta(minutes=5))
    tr = t.state.trades[0]
    assert abs(tr.pnl_gross - 475.0) < 1e-9, tr.pnl_gross
    assert abs(tr.commission - 5.0) < 1e-9, tr.commission
    assert abs(tr.slippage - 25.0) < 1e-9, tr.slippage
    assert abs(tr.pnl_net - 470.0) < 1e-9, tr.pnl_net
    assert abs(tr.fill_entry_price - 5000.25) < 1e-9
    assert abs(tr.fill_exit_price - 5009.75) < 1e-9
    print('slippage_ok')

def test_zero_slippage():
    t2 = BeginnerTrader(seed=1, slippage_ticks_per_side=0.0)
    now = pd.Timestamp('2026-01-01T14:00:00Z')
    t2.enter_trade({'side':'LONG','contracts':1,'entry_price':5000.0,'target_price':5010.0,'stop_price':4990.0,'session':'day'}, now)
    t2.exit_trade({'exit_price':5010.0,'exit_reason':'TARGET'}, now + pd.Timedelta(minutes=5))
    tr2 = t2.state.trades[0]
    assert abs(tr2.pnl_gross - 500.0) < 1e-9, tr2.pnl_gross
    assert abs(tr2.pnl_net - 495.0) < 1e-9, tr2.pnl_net
    assert abs(tr2.slippage - 0.0) < 1e-9, tr2.slippage
    print('zero_slippage_ok')

if __name__ == '__main__':
    test_slippage()
    test_zero_slippage()
    print('SMOKE_OK')
