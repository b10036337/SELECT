from __future__ import annotations

import argparse
from pathlib import Path

from .backtest import run_backtest, write_backtest_report
from .config import ScreenerConfig
from .pipeline import load_csv_inputs, run_screen


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default="config/screener.yaml")
    parser.add_argument("--data-dir", default="data/processed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Taiwan stock screener and backtests from prepared CSV inputs.")
    subparsers = parser.add_subparsers(dest="command")

    screen_parser = subparsers.add_parser("screen", help="Generate latest stock recommendations.")
    _add_common_args(screen_parser)
    screen_parser.add_argument("--output", default="reports/recommendations.csv")

    backtest_parser = subparsers.add_parser("backtest", help="Run historical backtest and performance report.")
    _add_common_args(backtest_parser)
    backtest_parser.add_argument("--output-dir", default="reports/backtest")

    # Backward-compatible default: `select-tw-update --config ... --output ...` still screens.
    parser.add_argument("--config", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    if args.command == "backtest":
        config = ScreenerConfig.load(args.config)
        fundamentals, chips, prices = load_csv_inputs(Path(args.data_dir))
        result = run_backtest(config, fundamentals, chips, prices)
        write_backtest_report(result, Path(args.output_dir))
        print(f"wrote backtest report to {args.output_dir}")
        return

    config_path = args.config or "config/screener.yaml"
    data_dir = args.data_dir or "data/processed"
    output_path = args.output or "reports/recommendations.csv"
    config = ScreenerConfig.load(config_path)
    fundamentals, chips, prices = load_csv_inputs(Path(data_dir))
    recommendations = run_screen(config, fundamentals, chips, prices)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_csv(output, index=False)
    print(f"wrote {len(recommendations)} recommendations to {output}")


if __name__ == "__main__":
    main()
