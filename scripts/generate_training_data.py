#!/usr/bin/env python3
import argparse
from pathlib import Path
import pandas as pd
from heater_controller.thermal import generate_training_data

p = argparse.ArgumentParser(description="Generate explicitly simulated heater-duty examples.")
p.add_argument("profile"); p.add_argument("--output", default="artifacts/simulated_training.csv")
p.add_argument("--seed", type=int, default=42); a = p.parse_args()
profile = pd.read_csv(a.profile, parse_dates=["timestamp"]).set_index("timestamp")
data = generate_training_data(profile, seed=a.seed)
Path(a.output).parent.mkdir(parents=True, exist_ok=True); data.to_csv(a.output)
print(f"Saved {len(data)} SIMULATED thermal/heater rows to {a.output}")
