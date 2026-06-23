from __future__ import annotations

import pandas as pd

from select_tw_screener.config import ScreenerConfig
from select_tw_screener.pipeline import run_screen
from select_tw_screener.price_stage import classify_price_stage


def _prices(stock_id: str) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=80, freq="B")
    closes = [100 + i * 0.05 for i in range(60)] + [103, 102, 102.5, 103, 102.8, 103.2, 103.5, 103.1, 103.4, 103.6, 103.8, 104, 104.1, 104.2, 104.3, 104.4, 104.5, 104.6, 104.7, 106]
    volumes = [1000] * 79 + [1400]
    return pd.DataFrame({"stock_id": stock_id, "date": dates, "close": closes, "volume": volumes})


def test_classify_completed_base() -> None:
    config = ScreenerConfig.load("config/screener.yaml")
    assert classify_price_stage(_prices("2330"), config.get("price_stage")) == "completed_base"


def test_run_screen_recommends_good_completed_base_stock() -> None:
    config = ScreenerConfig.load("config/screener.yaml")
    fundamentals = pd.DataFrame([
        {"stock_id": "2330", "revenue_growth_yoy": 25, "operating_margin": 25, "roe": 25, "eps_growth_yoy": 35, "debt_ratio_inverse": 90}
    ])
    chips = pd.DataFrame([
        {"stock_id": "2330", "foreign_net_buy_ratio_5d": 1, "investment_trust_net_buy_ratio_5d": 1, "dealer_net_buy_ratio_5d": 0.5, "margin_balance_change_5d_inverse": 12, "main_holder_ratio_change_4w": 4}
    ])
    result = run_screen(config, fundamentals, chips, _prices("2330"))
    assert result.loc[0, "stock_id"] == "2330"
    assert result.loc[0, "total_score"] >= 90
