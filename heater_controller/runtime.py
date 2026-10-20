"""Small, hardware-independent inference boundary for Raspberry Pi deployment."""
from pathlib import Path

import joblib
import pandas as pd

from .controllers import MLPPriceAwareController
from .training import FEATURES


def load_model(path):
    bundle = joblib.load(Path(path))
    if not isinstance(bundle, dict) or "model" not in bundle:
        raise ValueError("Model file is not a heater-controller joblib bundle")
    if bundle.get("features") != FEATURES:
        raise ValueError(f"Model features must be {FEATURES}, found {bundle.get('features')}")
    return bundle["model"]


def controller_step(model, indoor_temp, outdoor_temp, prices, heater_power_kw=2.0):
    prices = pd.Series([float(price) for price in prices], dtype=float)
    if prices.empty:
        raise ValueError("At least the current electricity price is required")
    controller = MLPPriceAwareController(model, heater_power_kw)
    duty = controller.choose(float(indoor_temp), float(outdoor_temp), prices)
    features = pd.DataFrame([{
        "indoor_temp": float(indoor_temp),
        "outdoor_temp": float(outdoor_temp),
        "heater_duty": duty,
    }])
    return {
        "heater_duty": duty,
        "predicted_next_temp": float(model.predict(features)[0]),
        "simulated_heater_command": "SIMULATED_ON" if duty > 0 else "SIMULATED_OFF",
    }
