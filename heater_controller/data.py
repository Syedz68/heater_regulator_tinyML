"""Input normalization and hourly timestamp alignment."""
from pathlib import Path
import pandas as pd

PRICE_FACTORS = {"EUR/MWh": ("EUR/kWh", .001), "EUR-MWh": ("EUR/kWh", .001),
                 "SEK/MWh": ("SEK/kWh", .001), "SEK/kWh": ("SEK/kWh", 1.),
                 "EUR/kWh": ("EUR/kWh", 1.)}

def parse_timestamps(values, timezone="Europe/Stockholm"):
    text = values.astype(str).str.strip()
    aware = text.str.contains(r"(?:Z|[+-]\d\d:?\d\d)$", regex=True)
    if aware.all():
        return pd.DatetimeIndex(pd.to_datetime(text, errors="raise", utc=True))
    if aware.any():
        raise ValueError("Do not mix timezone-aware and naive timestamps")
    parsed = pd.to_datetime(text, errors="raise")
    localized = parsed.dt.tz_localize(timezone, ambiguous="infer", nonexistent="shift_forward")
    return pd.DatetimeIndex(localized.dt.tz_convert("UTC"))

def hourly_align(df, timezone="Europe/Stockholm", max_gap_hours=3):
    if "timestamp" not in df:
        raise ValueError("Missing required column: timestamp")
    work = df.copy()
    work.index = parse_timestamps(work.pop("timestamp"), timezone)
    work.index.name = "timestamp"
    result = work.sort_index().groupby(level=0).mean(numeric_only=True).resample("1h").mean()
    result = result.interpolate(limit=max_gap_hours, limit_area="inside")
    return result

def convert_price(values, unit):
    if unit not in PRICE_FACTORS:
        raise ValueError(f"Unsupported price unit {unit!r}; choose one of {sorted(PRICE_FACTORS)}")
    target, factor = PRICE_FACTORS[unit]
    return values.astype(float) * factor, target

def load_canonical_csv(path, timezone="Europe/Stockholm", price_unit="EUR/MWh"):
    df = pd.read_csv(path)
    missing = {"timestamp", "outdoor_temp", "price"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    result = hourly_align(df, timezone)
    result["price"], result.attrs["price_unit"] = convert_price(result["price"], price_unit)
    return result.dropna(subset=["outdoor_temp", "price"])

def load_smhi_temperature(path):
    raw = pd.read_csv(path, sep=";", skiprows=9, encoding="utf-8-sig")
    raw = raw.rename(columns={"Lufttemperatur": "outdoor_temp"})
    raw["timestamp"] = raw["Datum"].astype(str) + " " + raw["Tid (UTC)"].astype(str) + "+00:00"
    return hourly_align(raw[["timestamp", "outdoor_temp"]], "UTC")

def load_se3_prices(path):
    raw = pd.read_csv(path)
    raw = raw.loc[raw["bidding_zone"].eq("SE3")].copy()
    if raw.empty:
        raise ValueError("No SE3 prices found")
    units = set(raw["price_unit"].dropna().unique())
    if units != {"EUR-MWh"}:
        raise ValueError(f"Expected a single EUR-MWh price unit, found {sorted(units)}")
    raw["timestamp"] = raw["start_time_utc"] + "+00:00"
    result = hourly_align(raw[["timestamp", "price"]], "UTC")
    result["price"], result.attrs["price_unit"] = convert_price(result["price"], "EUR-MWh")
    return result

def prepare_repository_profile(smhi_path, prices_path):
    joined = load_smhi_temperature(smhi_path).join(load_se3_prices(prices_path), how="inner").dropna()
    joined.attrs["price_unit"] = "EUR/kWh"
    if joined.empty:
        raise ValueError("Weather and price inputs have no overlapping hourly timestamps")
    return joined
