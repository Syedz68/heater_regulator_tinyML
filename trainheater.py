"""Backward-compatible training entry point. Prefer scripts/train_mlp.py."""
import json
import sys
from heater_controller.training import load_training_csv, train_model

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python trainheater.py simulated_training.csv")
    _, result = train_model(load_training_csv(sys.argv[1]), "heater_mlp.joblib", "test_predictions.csv")
    print("SIMULATED-DATA metrics:\n" + json.dumps(result, indent=2))
