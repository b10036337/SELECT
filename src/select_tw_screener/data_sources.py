from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import requests


@dataclass(frozen=True)
class TwseClient:
    """Small TWSE open-data client for raw daily files used by the pipeline."""

    timeout: int = 30

    def fetch_stock_day(self, stock_id: str, day: date) -> pd.DataFrame:
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params: dict[str, Any] = {"response": "json", "date": day.strftime("%Y%m%d"), "stockNo": stock_id}
        payload = requests.get(url, params=params, timeout=self.timeout).json()
        rows = payload.get("data", [])
        columns = payload.get("fields", [])
        return pd.DataFrame(rows, columns=columns)

    def fetch_institutional_trades(self, day: date) -> pd.DataFrame:
        url = "https://www.twse.com.tw/rwd/zh/fund/T86"
        params: dict[str, Any] = {"response": "json", "date": day.strftime("%Y%m%d"), "selectType": "ALL"}
        payload = requests.get(url, params=params, timeout=self.timeout).json()
        return pd.DataFrame(payload.get("data", []), columns=payload.get("fields", []))


def write_raw_snapshot(frame: pd.DataFrame, output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.csv"
    frame.to_csv(path, index=False)
    return path
