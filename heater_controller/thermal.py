"""One-zone thermal simulator; no physical heater or GPIO is controlled."""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class ThermalParameters:
    heat_loss_per_hour: float = .08
    heater_gain_c_per_hour: float = 2.2
    process_noise_std: float = .03

def thermal_step(indoor_temp, outdoor_temp, heater_duty, params=ThermalParameters(), noise=0.):
    duty = float(np.clip(heater_duty, 0., 1.))
    return indoor_temp + params.heat_loss_per_hour * (outdoor_temp - indoor_temp) + params.heater_gain_c_per_hour * duty + noise

def generate_training_data(profile, initial_temp=20., params=ThermalParameters(), seed=42):
    rng, indoor, rows = np.random.default_rng(seed), initial_temp, []
    for timestamp, row in profile.iterrows():
        base = np.clip((20. - indoor) / 2., 0, 1)
        duty = float(np.clip(base + rng.normal(0, .28), 0, 1))
        rows.append((timestamp, indoor, row.outdoor_temp, duty))
        indoor = thermal_step(indoor, row.outdoor_temp, duty, params, rng.normal(0, params.process_noise_std))
    return pd.DataFrame(rows, columns=["timestamp", "indoor_temp", "outdoor_temp", "heater_duty"]).set_index("timestamp")
