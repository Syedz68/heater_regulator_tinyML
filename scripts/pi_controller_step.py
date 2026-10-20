#!/usr/bin/env python3
"""Run one safe, simulation-only controller decision on a Raspberry Pi."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from heater_controller.runtime import controller_step, load_model


def main():
    parser = argparse.ArgumentParser(description="Run one simulated Raspberry Pi heater decision")
    parser.add_argument("--model", default="artifacts/heater_mlp.joblib")
    parser.add_argument("--indoor-temp", type=float, required=True)
    parser.add_argument("--outdoor-temp", type=float, required=True)
    parser.add_argument("--prices", required=True,
                        help="Comma-separated current and upcoming prices per kWh")
    parser.add_argument("--heater-power-kw", type=float, default=2.0)
    parser.add_argument("--log", help="Optional CSV decision log")
    args = parser.parse_args()

    prices = [float(value.strip()) for value in args.prices.split(",") if value.strip()]
    result = controller_step(load_model(args.model), args.indoor_temp, args.outdoor_temp,
                             prices, args.heater_power_kw)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "indoor_temp": args.indoor_temp,
        "outdoor_temp": args.outdoor_temp,
        "current_price_per_kwh": prices[0],
        **result,
    }
    print(json.dumps(record, indent=2))

    if args.log:
        path = Path(args.log)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=record)
            if write_header:
                writer.writeheader()
            writer.writerow(record)


if __name__ == "__main__":
    main()
