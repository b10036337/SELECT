from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import ScreenerConfig
from .price_stage import classify_price_stage
from .scoring import score_factor_frame


REQUIRED_PRICE_COLUMNS = {"stock_id", "date", "close", "volume"}


def run_screen(config: ScreenerConfig, fundamentals: pd.DataFrame, chips: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_PRICE_COLUMNS - set(prices.columns)
    if missing:
        raise ValueError(f"prices missing required columns: {sorted(missing)}")

    fundamental_scored = score_factor_frame(
        fundamentals,
        config.get("fundamental_score", "weights", default={}),
        config.get("fundamental_score", "thresholds", default={}),
        "fundamental_score",
    )
    chip_scored = score_factor_frame(
        chips,
        config.get("chip_score", "weights", default={}),
        config.get("chip_score", "thresholds", default={}),
        "chip_score",
    )

    stages = [
        {"stock_id": stock_id, "price_stage": classify_price_stage(group, config.get("price_stage", default={}))}
        for stock_id, group in prices.groupby("stock_id")
    ]
    stage_frame = pd.DataFrame(stages)
    latest_prices = prices.sort_values("date").groupby("stock_id").tail(1)[["stock_id", "date", "close"]]

    merged = fundamental_scored.merge(chip_scored, on="stock_id", how="inner")
    merged = merged.merge(stage_frame, on="stock_id", how="inner").merge(latest_prices, on="stock_id", how="left")

    total_weights = config.get("recommendation", "total_weights", default={"fundamental": 0.45, "chip": 0.35, "price_setup": 0.20})
    merged["price_setup_score"] = merged["price_stage"].map({"completed_base": 100, "consolidating": 60, "correction": 30, "neutral": 40, "extended": 20}).fillna(0)
    merged["total_score"] = (
        merged["fundamental_score"] * total_weights["fundamental"]
        + merged["chip_score"] * total_weights["chip"]
        + merged["price_setup_score"] * total_weights["price_setup"]
    ).round(2)

    minimum = config.get("run", "minimum_total_score", default=70)
    required_stage = config.get("run", "require_price_stage", default="completed_base")
    limit = config.get("run", "recommendation_limit", default=30)
    return (
        merged[(merged["total_score"] >= minimum) & (merged["price_stage"] == required_stage)]
        .sort_values(["total_score", "fundamental_score", "chip_score"], ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def load_csv_inputs(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_csv(data_dir / "fundamentals.csv"),
        pd.read_csv(data_dir / "chips.csv"),
        pd.read_csv(data_dir / "prices.csv", parse_dates=["date"]),
    )
