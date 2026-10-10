"""Chronological CPU training for the one-hour temperature predictor."""
from pathlib import Path
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["indoor_temp", "outdoor_temp", "heater_duty"]

def chronological_split(data, train_fraction=.70, val_fraction=.15):
    n = len(data); a, b = int(n * train_fraction), int(n * (train_fraction + val_fraction))
    if a == 0 or b <= a or b >= n:
        raise ValueError("Not enough rows for non-empty chronological splits")
    return data.iloc[:a], data.iloc[a:b], data.iloc[b:]

def regression_metrics(actual, predicted):
    return {"mae_c": float(mean_absolute_error(actual, predicted)),
            "rmse_c": float(np.sqrt(mean_squared_error(actual, predicted)))}

def train_model(data, model_path, predictions_path):
    ordered = data.sort_index().copy()
    ordered["target_temp"] = ordered["indoor_temp"].shift(-1)
    usable = ordered.dropna(subset=FEATURES + ["target_temp"])
    if len(usable) < 100:
        raise ValueError(f"Only {len(usable)} usable rows; need at least 100")
    train, validation, test = chronological_split(usable)
    model = make_pipeline(StandardScaler(), MLPRegressor(hidden_layer_sizes=(8, 4), activation="relu",
        solver="adam", alpha=.001, max_iter=3000, random_state=42))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model.fit(train[FEATURES], train["target_temp"])
    val_prediction, test_prediction = model.predict(validation[FEATURES]), model.predict(test[FEATURES])
    results = {"validation_mlp": regression_metrics(validation.target_temp, val_prediction),
               "test_mlp": regression_metrics(test.target_temp, test_prediction),
               "test_persistence": regression_metrics(test.target_temp, test.indoor_temp)}
    joblib.dump({"model": model, "features": FEATURES, "simulated_training": True}, model_path)
    pd.DataFrame({"timestamp": test.index, "actual_temp": test.target_temp,
                  "predicted_temp": test_prediction, "persistence_temp": test.indoor_temp}).to_csv(predictions_path, index=False)
    return model, results

def load_training_csv(path):
    df = pd.read_csv(path)
    missing = {"timestamp", *FEATURES} - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").drop_duplicates("timestamp").set_index("timestamp")
