#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from heater_controller.training import load_training_csv, train_model

p = argparse.ArgumentParser(); p.add_argument("data")
p.add_argument("--model", default="artifacts/heater_mlp.joblib")
p.add_argument("--predictions", default="artifacts/test_predictions.csv"); a = p.parse_args()
Path(a.model).parent.mkdir(parents=True, exist_ok=True); Path(a.predictions).parent.mkdir(parents=True, exist_ok=True)
_, metrics = train_model(load_training_csv(a.data), a.model, a.predictions)
print("SIMULATED-DATA model metrics:\n" + json.dumps(metrics, indent=2))
print(f"Saved {a.model} and {a.predictions}")
