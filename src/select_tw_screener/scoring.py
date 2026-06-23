from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def _bucket_score(value: float, thresholds: list[float]) -> float:
    if pd.isna(value):
        return 0.0
    passed = sum(value >= threshold for threshold in thresholds)
    return min(100.0, passed / len(thresholds) * 100.0)


def weighted_bucket_score(row: pd.Series, weights: Mapping[str, float], thresholds: Mapping[str, list[float]]) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    score = 0.0
    for metric, weight in weights.items():
        metric_thresholds = thresholds.get(metric, [])
        if not metric_thresholds:
            continue
        score += _bucket_score(float(row.get(metric, float("nan"))), metric_thresholds) * weight
    return round(score / total_weight, 2)


def score_factor_frame(data: pd.DataFrame, weights: Mapping[str, float], thresholds: Mapping[str, list[float]], score_name: str) -> pd.DataFrame:
    if data.empty:
        result = data.copy()
        result[score_name] = []
        return result
    result = data.copy()
    result[score_name] = result.apply(lambda row: weighted_bucket_score(row, weights, thresholds), axis=1)
    return result
