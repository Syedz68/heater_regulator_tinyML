#!/usr/bin/env python3
"""Create reproducible static plots from the latest simulated artifacts."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "plots"
COLORS = {"Static hysteresis": "#4C78A8", "Price aware rule": "#F58518", "MLP price aware": "#54A24B"}
FILES = {"Static hysteresis": "static_hysteresis_simulated.csv",
         "Price aware rule": "price_aware_rule_simulated.csv",
         "MLP price aware": "mlp_price_aware_simulated.csv"}

def finish(fig, name):
    fig.savefig(OUT / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 13, "axes.labelsize": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .22, "figure.titlesize": 15})

    predictions = pd.read_csv(ROOT / "artifacts/test_predictions.csv", parse_dates=["timestamp"])
    view = predictions.iloc[:24 * 14]
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(view.timestamp, view.actual_temp, color="#222222", lw=2, label="Actual simulated temperature")
    ax.plot(view.timestamp, view.predicted_temp, color="#4C78A8", lw=1.6, label="MLP prediction")
    ax.plot(view.timestamp, view.persistence_temp, color="#E45756", lw=1.1, ls="--", label="Persistence baseline")
    ax.set(title="Next hour temperature predictions on the simulated test set",
           ylabel="Indoor temperature (°C)", xlabel="UTC date")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(.5, 1.16))
    fig.autofmt_xdate(rotation=0); finish(fig, "model_predictions.png")

    details = {}
    for label, filename in FILES.items():
        details[label] = pd.read_csv(ROOT / "artifacts/evaluation" / filename, parse_dates=["timestamp"])
    base = details["Static hysteresis"]
    cold_index = base.outdoor_temp.rolling(24 * 7, center=True, min_periods=24).mean().idxmin()
    start = base.timestamp.iloc[max(0, cold_index - 24 * 3)]
    end = start + pd.Timedelta(days=14)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[2, 1])
    for label, frame in details.items():
        clip = frame[(frame.timestamp >= start) & (frame.timestamp < end)]
        ax1.plot(clip.timestamp, clip.indoor_temp, lw=1.4, color=COLORS[label], label=label)
        ax2.plot(clip.timestamp, clip.heater_duty, lw=1.0, color=COLORS[label], label=label)
    outdoor = base[(base.timestamp >= start) & (base.timestamp < end)]
    ax1.plot(outdoor.timestamp, outdoor.outdoor_temp, color="#888888", lw=1, alpha=.65, label="Outdoor temperature")
    ax1.axhspan(19, 21, color="#72B7B2", alpha=.14, label="19–21 °C comfort band")
    ax1.axhline(19, color="#555555", lw=.7, ls=":"); ax1.axhline(21, color="#555555", lw=.7, ls=":")
    ax1.set(ylabel="Temperature (°C)", title="Controller behavior during a representative cold period")
    ax2.set(ylabel="Heater duty", xlabel="UTC date", ylim=(-.03, 1.03))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2)); ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax1.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(.5, 1.2))
    fig.tight_layout(); finish(fig, "controller_temperature_and_duty.png")

    fig, ax = plt.subplots(figsize=(11, 4.8))
    for label, frame in details.items():
        ax.plot(frame.timestamp, frame.cost.cumsum(), lw=2, color=COLORS[label], label=label)
    ax.set(title="Cumulative simulated SE3 spot price cost", ylabel="Cumulative cost (EUR)", xlabel="UTC date")
    ax.legend(frameon=False); finish(fig, "cumulative_cost.png")

    summary = pd.read_csv(ROOT / "artifacts/evaluation/simulated_summary.csv")
    summary["label"] = summary.controller.map({"static_hysteresis": "Static hysteresis",
        "price_aware_rule": "Price aware rule", "mlp_price_aware": "MLP price aware"})
    specs = [("estimated_cost", "Estimated spot cost", "EUR"),
             ("estimated_energy_kwh", "Estimated energy", "kWh"),
             ("degree_hours_outside", "Comfort violation", "Degree-hours"),
             ("heater_switches", "Heater switching", "Switches")]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.4))
    for ax, (column, title, unit) in zip(axes.flat, specs):
        vals = summary[column].to_numpy(); labels = summary.label.tolist()
        bars = ax.barh(labels, vals, color=[COLORS[x] for x in labels])
        ax.set_title(title); ax.set_xlabel(unit); ax.grid(axis="y", visible=False)
        ax.bar_label(bars, labels=[f"{v:,.1f}" if isinstance(v, (float, np.floating)) else f"{v:,}" for v in vals], padding=4)
        ax.set_xlim(0, vals.max() * 1.18)
    fig.suptitle("Simulated controller tradeoffs", y=.99)
    fig.tight_layout(); finish(fig, "controller_summary.png")
    print(f"Created 4 plots in {OUT}")

if __name__ == "__main__": main()
