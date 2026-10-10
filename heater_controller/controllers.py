"""Controller policies returning simulated duty from zero to one."""
import numpy as np
import pandas as pd

class HysteresisController:
    def __init__(self, low=19., high=21.): self.low, self.high, self.on = low, high, False
    def choose(self, indoor, outdoor, prices):
        if indoor < self.low: self.on = True
        elif indoor > self.high: self.on = False
        return float(self.on)

class PriceAwareRuleController:
    def choose(self, indoor, outdoor, prices):
        cheap = float(prices.iloc[0]) <= float(prices.quantile(.35))
        target = 20.8 if cheap else 19.2
        if indoor < 19.: return 1.
        if indoor > 21.: return 0.
        return float(np.clip((target - indoor) / 1.4, 0, 1))

class MLPPriceAwareController:
    def __init__(self, model, heater_power_kw=2., comfort_penalty=5.):
        self.model, self.power, self.penalty = model, heater_power_kw, comfort_penalty
    def choose(self, indoor, outdoor, prices):
        duties = np.linspace(0, 1, 11)
        features = pd.DataFrame({"indoor_temp": indoor, "outdoor_temp": outdoor, "heater_duty": duties})
        predicted = self.model.predict(features)
        violation = np.maximum(19. - predicted, 0) ** 2 + np.maximum(predicted - 21., 0) ** 2
        scores = self.power * duties * float(prices.iloc[0]) + self.penalty * violation
        if indoor < 19.: scores[duties < .5] += 100
        if indoor > 21.: scores[duties > 0] += 100
        return float(duties[int(np.argmin(scores))])
