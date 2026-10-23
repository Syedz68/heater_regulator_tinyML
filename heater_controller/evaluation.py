"""Fair common-profile controller simulation and metrics."""
from simulation.simulation import InitDefaultSimEnv,SimEnv,Heater,Ventilation,Room,Screen
import pandas as pd
from .thermal import ThermalParameters, thermal_step

def energy_and_cost(duty, price_per_kwh, heater_power_kw, hours=1.):
    energy = heater_power_kw * float(duty) * hours
    return energy, energy * float(price_per_kwh)

def simulate_controller(name, controller, profile, heater_power_kw=2., initial_temp=20., params=ThermalParameters()):
    indoor, previous_on, switches, records = initial_temp, False, 0, []

    simInstance = InitDefaultSimEnv(initial_temp,0,heater_power_kw*1000)
    timePassedInMinutes = 0
    for i, (timestamp, row) in enumerate(profile.iterrows()):
        duty = controller.choose(simInstance.insideTemperatureInCelsius, float(row.outdoor_temp), profile["price"].iloc[i:i + 24])
        energy, cost = energy_and_cost(duty, row.price, heater_power_kw)

        on = duty > 0; switches += int(on != previous_on)
        
        degree_hours = max(19. - simInstance.insideTemperatureInCelsius, 0.) + max(simInstance.insideTemperatureInCelsius - 21., 0.)
        records.append((timestamp, simInstance.insideTemperatureInCelsius, row.outdoor_temp, row.price, duty, energy, cost, degree_hours))
        previous_on = on
        simInstance.outsideTemperatureInCelsius = row.outdoor_temp
        simInstance.heater.output = duty
        timePassedInMinutes += 15
        # Run simulation in 60 smaller 1 minute steps rather than 1 big 60 minute step
        # for better accuracy
        for x in range(0,60): 
            simInstance.tick(1)
        
    detail = pd.DataFrame(records, columns=["timestamp", "indoor_temp", "outdoor_temp", "price_per_kwh",
        "heater_duty", "energy_kwh", "cost", "degree_hours_outside"])
    summary = {"controller": name, "simulated": True, "estimated_cost": detail.cost.sum(),
        "estimated_energy_kwh": detail.energy_kwh.sum(), "hours_outside_comfort": int((detail.degree_hours_outside > 0).sum()),
        "degree_hours_outside": detail.degree_hours_outside.sum(), "heater_switches": switches}
    return detail, summary

