from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ScreenerConfig
from .pipeline import run_screen


@dataclass(frozen=True)
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    summary: dict[str, Any]


def _latest_snapshot(frame: pd.DataFrame, as_of_date: pd.Timestamp) -> pd.DataFrame:
    if "date" not in frame.columns:
        return frame.copy()
    eligible = frame[pd.to_datetime(frame["date"]) <= as_of_date].copy()
    if eligible.empty:
        return eligible.drop(columns=["date"], errors="ignore")
    return eligible.sort_values("date").groupby("stock_id").tail(1).drop(columns=["date"], errors="ignore")


def _rebalance_dates(prices: pd.DataFrame, frequency: str) -> list[pd.Timestamp]:
    trading_days = pd.Series(pd.to_datetime(prices["date"]).sort_values().unique())
    if frequency == "D":
        return list(trading_days)
    grouped = pd.DataFrame({"date": trading_days})
    return list(grouped.groupby(grouped["date"].dt.to_period(frequency))["date"].max())


def _next_trading_day(trading_days: list[pd.Timestamp], day: pd.Timestamp) -> pd.Timestamp | None:
    for trading_day in trading_days:
        if trading_day > day:
            return trading_day
    return None


def _exit_day(trading_days: list[pd.Timestamp], entry_day: pd.Timestamp, holding_days: int) -> pd.Timestamp | None:
    future_days = [day for day in trading_days if day >= entry_day]
    if len(future_days) <= holding_days:
        return None
    return future_days[holding_days]


def run_backtest(config: ScreenerConfig, fundamentals: pd.DataFrame, chips: pd.DataFrame, prices: pd.DataFrame) -> BacktestResult:
    """Run a point-in-time equal-weight backtest using the configured screener."""
    backtest_config = config.get("backtest", default={})
    frequency = backtest_config.get("rebalance_frequency", "W")
    holding_days = int(backtest_config.get("holding_days", 20))
    max_positions = int(backtest_config.get("max_positions", config.get("run", "recommendation_limit", default=30)))
    transaction_cost_bps = float(backtest_config.get("transaction_cost_bps", 14.25))

    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    trading_days = list(pd.Series(prices["date"].sort_values().unique()))
    price_lookup = prices.set_index(["stock_id", "date"])["close"].sort_index()
    trades: list[dict[str, Any]] = []

    for signal_date in _rebalance_dates(prices, frequency):
        entry_date = _next_trading_day(trading_days, signal_date)
        if entry_date is None:
            continue
        exit_date = _exit_day(trading_days, entry_date, holding_days)
        if exit_date is None:
            continue

        price_history = prices[prices["date"] <= signal_date]
        recommendations = run_screen(
            config,
            _latest_snapshot(fundamentals, signal_date),
            _latest_snapshot(chips, signal_date),
            price_history,
        ).head(max_positions)

        for row in recommendations.itertuples(index=False):
            stock_id = getattr(row, "stock_id")
            try:
                entry_price = float(price_lookup.loc[(stock_id, entry_date)])
                exit_price = float(price_lookup.loc[(stock_id, exit_date)])
            except KeyError:
                continue
            gross_return = exit_price / entry_price - 1
            net_return = gross_return - transaction_cost_bps / 10_000 * 2
            trades.append(
                {
                    "signal_date": signal_date,
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "stock_id": stock_id,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "gross_return": gross_return,
                    "net_return": net_return,
                    "total_score": getattr(row, "total_score"),
                    "fundamental_score": getattr(row, "fundamental_score"),
                    "chip_score": getattr(row, "chip_score"),
                    "price_stage": getattr(row, "price_stage"),
                }
            )

    trades_frame = pd.DataFrame(trades)
    equity_curve = _build_equity_curve(trades_frame)
    summary = _summarize(trades_frame, equity_curve)
    return BacktestResult(trades=trades_frame, equity_curve=equity_curve, summary=summary)


def _build_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["exit_date", "period_return", "equity", "drawdown"])
    period_returns = trades.groupby("exit_date")["net_return"].mean().reset_index(name="period_return")
    period_returns = period_returns.sort_values("exit_date")
    period_returns["equity"] = (1 + period_returns["period_return"]).cumprod()
    running_max = period_returns["equity"].cummax()
    period_returns["drawdown"] = period_returns["equity"] / running_max - 1
    return period_returns


def _summarize(trades: pd.DataFrame, equity_curve: pd.DataFrame) -> dict[str, Any]:
    if trades.empty or equity_curve.empty:
        return {
            "trade_count": 0,
            "win_rate": 0.0,
            "average_trade_return": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "profit_factor": 0.0,
        }
    wins = trades[trades["net_return"] > 0]
    losses = trades[trades["net_return"] < 0]
    gross_profit = wins["net_return"].sum()
    gross_loss = abs(losses["net_return"].sum())
    return {
        "trade_count": int(len(trades)),
        "win_rate": round(float(len(wins) / len(trades)), 4),
        "average_trade_return": round(float(trades["net_return"].mean()), 4),
        "total_return": round(float(equity_curve["equity"].iloc[-1] - 1), 4),
        "max_drawdown": round(float(equity_curve["drawdown"].min()), 4),
        "profit_factor": round(float(gross_profit / gross_loss), 4) if gross_loss else 0.0,
    }


def write_backtest_report(result: BacktestResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    result.trades.to_csv(output_dir / "backtest_trades.csv", index=False)
    result.equity_curve.to_csv(output_dir / "backtest_equity.csv", index=False)
    pd.DataFrame([result.summary]).to_csv(output_dir / "backtest_summary.csv", index=False)
    (output_dir / "backtest_report.md").write_text(_markdown_report(result.summary), encoding="utf-8")


def _markdown_report(summary: dict[str, Any]) -> str:
    rows = "\n".join(f"| {key} | {value} |" for key, value in summary.items())
    return "# Backtest Performance Report\n\n| Metric | Value |\n| --- | --- |\n" + rows + "\n"
