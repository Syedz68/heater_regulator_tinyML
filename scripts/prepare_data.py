#!/usr/bin/env python3
import argparse
from pathlib import Path
from heater_controller.data import load_canonical_csv, prepare_repository_profile

p = argparse.ArgumentParser(description="Prepare hourly weather and SE3 prices (simulation input).")
p.add_argument("--input"); p.add_argument("--smhi"); p.add_argument("--prices")
p.add_argument("--price-unit", default="EUR/MWh"); p.add_argument("--timezone", default="Europe/Stockholm")
p.add_argument("--output", required=True); a = p.parse_args()
if a.input: frame = load_canonical_csv(a.input, a.timezone, a.price_unit)
elif a.smhi and a.prices: frame = prepare_repository_profile(a.smhi, a.prices)
else: p.error("provide --input, or both --smhi and --prices")
Path(a.output).parent.mkdir(parents=True, exist_ok=True); frame.to_csv(a.output)
print(f"Prepared {len(frame)} hourly UTC rows; prices are {frame.attrs.get('price_unit', 'per kWh')}: {a.output}")
