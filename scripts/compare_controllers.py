#!/usr/bin/env python3
import argparse
from pathlib import Path
import joblib, pandas as pd
from heater_controller.controllers import HysteresisController, PriceAwareRuleController, MLPPriceAwareController
from heater_controller.evaluation import simulate_controller

p = argparse.ArgumentParser(); p.add_argument("profile"); p.add_argument("model")
p.add_argument("--heater-power-kw", type=float, default=2.); p.add_argument("--output-dir", default="artifacts/evaluation")
a = p.parse_args(); profile = pd.read_csv(a.profile, parse_dates=["timestamp"]).set_index("timestamp")
model = joblib.load(a.model)["model"]
controllers = [("static_hysteresis", HysteresisController()), ("price_aware_rule", PriceAwareRuleController()),
               ("mlp_price_aware", MLPPriceAwareController(model, a.heater_power_kw))]
out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True); summaries = []
for name, controller in controllers:
    detail, summary = simulate_controller(name, controller, profile, a.heater_power_kw)
    detail.to_csv(out / f"{name}_simulated.csv", index=False); summaries.append(summary)
summary_df = pd.DataFrame(summaries); summary_df.to_csv(out / "simulated_summary.csv", index=False)
print("SIMULATED comparison (spot price only; excludes taxes, network charges, retailer fees):")
print(summary_df.to_string(index=False))
