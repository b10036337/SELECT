from __future__ import annotations

import pandas as pd


def classify_price_stage(prices: pd.DataFrame, rules: dict) -> str:
    """Classify a stock into correction, consolidating, completed_base, extended, or neutral."""
    if len(prices) < 60:
        return "insufficient_data"

    frame = prices.sort_values("date").copy()
    close = frame["close"]
    volume = frame["volume"]
    latest = close.iloc[-1]
    high_60 = close.tail(60).max()
    low_20 = close.tail(20).min()
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]
    ma20_prev = close.rolling(20).mean().iloc[-6]
    avg_volume20 = volume.tail(20).mean()
    range20_pct = (close.tail(20).max() - low_20) / low_20 * 100
    drawdown_pct = (high_60 - latest) / high_60 * 100
    close_vs_ma20_pct = (latest - ma20) / ma20 * 100
    ma20_slope_pct = (ma20 - ma20_prev) / ma20_prev * 100
    ma20_vs_ma60_pct = (ma20 - ma60) / ma60 * 100
    volume_vs_avg = volume.iloc[-1] / avg_volume20 if avg_volume20 else 0
    gain_from_20d_low_pct = (latest - low_20) / low_20 * 100

    extended = rules["extended"]
    if gain_from_20d_low_pct >= extended["min_gain_from_20d_low_pct"] and close_vs_ma20_pct >= extended["min_close_vs_ma20_pct"]:
        return "extended"

    completed = rules["completed_base"]
    near_breakout = latest >= close.tail(20).max() * (1 - completed["breakout_buffer_pct"] / 100)
    if (
        range20_pct <= completed["max_20d_range_pct"]
        and close_vs_ma20_pct >= completed["min_close_vs_ma20_pct"]
        and ma20_vs_ma60_pct >= completed["min_ma20_vs_ma60_pct"]
        and volume_vs_avg >= completed["min_volume_vs_20d_avg"]
        and near_breakout
    ):
        return "completed_base"

    consolidating = rules["consolidating"]
    if range20_pct <= consolidating["max_20d_range_pct"] and abs(ma20_slope_pct) <= consolidating["max_ma20_slope_pct"]:
        return "consolidating"

    correction = rules["correction"]
    if drawdown_pct >= correction["min_drawdown_from_60d_high_pct"] and close_vs_ma20_pct <= correction["max_price_vs_ma20_pct"]:
        return "correction"

    return "neutral"
