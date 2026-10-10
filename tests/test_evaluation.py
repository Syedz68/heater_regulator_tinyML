import pandas as pd
from heater_controller.evaluation import energy_and_cost, simulate_controller
from heater_controller.controllers import HysteresisController

def test_energy_and_cost():
    energy, cost = energy_and_cost(.5, .2, 2.)
    assert energy == 1. and cost == .2

def test_hysteresis_comfort_recovery():
    profile = pd.DataFrame({"outdoor_temp": [5.] * 24, "price": [.1] * 24},
        index=pd.date_range("2025-01-01", periods=24, freq="h", tz="UTC"))
    detail, summary = simulate_controller("test", HysteresisController(), profile, initial_temp=18.5)
    assert detail.iloc[0].heater_duty == 1.
    assert detail.indoor_temp.max() < 22.5
    assert summary["heater_switches"] > 0
