import pandas as pd
from heater_controller.data import hourly_align, convert_price

def test_hourly_alignment_handles_spring_dst():
    df = pd.DataFrame({"timestamp": ["2025-03-30 00:00:00+01:00", "2025-03-30 01:00:00+01:00",
                                    "2025-03-30 03:00:00+02:00"], "outdoor_temp": [1., 2., 4.]})
    result = hourly_align(df)
    assert str(result.index.tz) == "UTC"
    assert len(result) == 3

def test_price_conversion_mwh_to_kwh():
    values, unit = convert_price(pd.Series([100.]), "EUR/MWh")
    assert values.iloc[0] == .1 and unit == "EUR/kWh"
