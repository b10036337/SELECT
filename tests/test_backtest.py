from __future__ import annotations

import pandas as pd

from select_tw_screener.backtest import run_backtest
from select_tw_screener.config import ScreenerConfig


def _price_panel() -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    closes = [100 + i * 0.05 for i in range(60)] + [103, 102, 102.5, 103, 102.8, 103.2, 103.5, 103.1, 103.4, 103.6, 103.8, 104, 104.1, 104.2, 104.3, 104.4, 104.5, 104.6, 104.7, 106]
    closes += [106 + i for i in range(20)]
    volumes = [1000] * 79 + [1400] + [1200] * 20
    return pd.DataFrame({"stock_id": "2330", "date": dates, "close": closes, "volume": volumes})


def test_run_backtest_outputs_trades_equity_and_summary() -> None:
    config = ScreenerConfig.load("config/screener.yaml")
    fundamentals = pd.DataFrame([
        {"date": "2026-01-01", "stock_id": "2330", "revenue_growth_yoy": 25, "operating_margin": 25, "roe": 25, "eps_growth_yoy": 35, "debt_ratio_inverse": 90}
    ])
    chips = pd.DataFrame([
        {"date": "2026-01-01", "stock_id": "2330", "foreign_net_buy_ratio_5d": 1, "investment_trust_net_buy_ratio_5d": 1, "dealer_net_buy_ratio_5d": 0.5, "margin_balance_change_5d_inverse": 12, "main_holder_ratio_change_4w": 4}
    ])
    result = run_backtest(config, fundamentals, chips, _price_panel())
    assert not result.trades.empty
    assert not result.equity_curve.empty
    assert result.summary["trade_count"] >= 1
