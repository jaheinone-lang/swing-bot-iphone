"""CLI: python -m swingbot.cli data/demo_prices.csv --equity 5000 --peak-equity 5000"""
import argparse
import csv
import json
from .strategy import evaluate_signal


def main():
    parser = argparse.ArgumentParser(description="Simulated swing signal; NO real trades")
    parser.add_argument("csv_path", help="CSV with date,high,low,close columns")
    parser.add_argument("--equity", type=float, default=5000.0)
    parser.add_argument("--peak-equity", type=float, default=5000.0)
    args = parser.parse_args()
    closes, highs, lows = [], [], []
    with open(args.csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            closes.append(float(row["close"]))
            highs.append(float(row["high"]))
            lows.append(float(row["low"]))
    result = evaluate_signal(
        closes, highs, lows,
        equity=args.equity, peak_equity=args.peak_equity,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
