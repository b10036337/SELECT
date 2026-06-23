from __future__ import annotations

import argparse
from pathlib import Path

from .config import ScreenerConfig
from .pipeline import load_csv_inputs, run_screen


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Taiwan stock screener from prepared CSV inputs.")
    parser.add_argument("--config", default="config/screener.yaml")
    parser.add_argument("--data-dir", default="data/processed")
    parser.add_argument("--output", default="reports/recommendations.csv")
    args = parser.parse_args()

    config = ScreenerConfig.load(args.config)
    fundamentals, chips, prices = load_csv_inputs(Path(args.data_dir))
    recommendations = run_screen(config, fundamentals, chips, prices)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(output, index=False)
    print(f"wrote {len(recommendations)} recommendations to {output}")


if __name__ == "__main__":
    main()
