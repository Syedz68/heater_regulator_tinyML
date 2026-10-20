import numpy as np
import pandas as pd
import pytest

from heater_controller.runtime import controller_step


class ThermalModel:
    def predict(self, frame):
        return (frame.indoor_temp + .08 * (frame.outdoor_temp - frame.indoor_temp)
                + 2.2 * frame.heater_duty).to_numpy()


def test_controller_step_returns_safe_simulated_result():
    result = controller_step(ThermalModel(), indoor_temp=18.5, outdoor_temp=2,
                             prices=[.15, .10, .20])
    assert .5 <= result["heater_duty"] <= 1
    assert np.isfinite(result["predicted_next_temp"])
    assert result["simulated_heater_command"] == "SIMULATED_ON"


def test_controller_step_requires_price():
    with pytest.raises(ValueError, match="price"):
        controller_step(ThermalModel(), 20, 5, [])
