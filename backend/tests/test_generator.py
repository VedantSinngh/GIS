"""
Tests for the synthetic hotspot generator.
Run from repo root: pytest backend/tests/test_generator.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pandas as pd
from synthetic.generator import generate_hotspots, _is_on_land

REQUIRED_VIIRS_COLS = {
    "latitude", "longitude", "bright_ti4", "bright_ti5", "scan", "track",
    "acq_date", "acq_time", "satellite", "instrument", "confidence", "frp", "daynight",
}
REQUIRED_ENRICHMENT_COLS = {
    "wind_speed_kmh", "wind_dir_deg", "temperature_c", "humidity_pct",
    "ndvi", "land_cover", "state", "source",
}


@pytest.fixture(scope="module")
def df():
    return generate_hotspots(days=10, seed=42)


def test_schema_has_viirs_columns(df):
    missing = REQUIRED_VIIRS_COLS - set(df.columns)
    assert not missing, f"Missing VIIRS columns: {missing}"


def test_schema_has_enrichment_columns(df):
    missing = REQUIRED_ENRICHMENT_COLS - set(df.columns)
    assert not missing, f"Missing enrichment columns: {missing}"


def test_non_empty(df):
    assert len(df) > 0, "Generator returned empty DataFrame"


def test_latitude_range(df):
    assert df["latitude"].between(6.0, 38.0).all(), "Latitudes out of India range"


def test_longitude_range(df):
    assert df["longitude"].between(67.0, 98.0).all(), "Longitudes out of India range"


def test_brightness_range(df):
    assert df["bright_ti4"].between(295, 370).all(), "bright_ti4 out of physical range"


def test_frp_range(df):
    assert df["frp"].between(0.3, 200).all(), "FRP out of physical range"


def test_ndvi_range(df):
    assert df["ndvi"].between(-0.1, 1.0).all(), "NDVI out of [−1, 1]"


def test_humidity_range(df):
    assert df["humidity_pct"].between(1, 100).all(), "Humidity out of [0,100]"


def test_confidence_values(df):
    assert set(df["confidence"].unique()).issubset({"l", "n", "h"}), "Invalid confidence values"


def test_satellite_values(df):
    assert set(df["satellite"].unique()).issubset({"N", "N20", "N21"}), "Invalid satellite values"


def test_daynight_values(df):
    assert set(df["daynight"].unique()).issubset({"D", "N"}), "Invalid daynight values"


def test_source_is_synthetic(df):
    assert (df["source"] == "synthetic").all(), "source field must be 'synthetic'"


def test_no_ocean_points(df):
    """All generated points must pass the coarse land check."""
    ocean_mask = df.apply(lambda r: not _is_on_land(r["latitude"], r["longitude"]), axis=1)
    assert not ocean_mask.any(), f"{ocean_mask.sum()} points failed land check"


def test_seed_determinism():
    """Same seed → identical output."""
    df1 = generate_hotspots(days=5, seed=99)
    df2 = generate_hotspots(days=5, seed=99)
    pd.testing.assert_frame_equal(df1, df2, check_dtype=False)


def test_different_seeds_differ():
    """Different seeds → different outputs."""
    df1 = generate_hotspots(days=5, seed=1)
    df2 = generate_hotspots(days=5, seed=2)
    assert not df1["latitude"].equals(df2["latitude"]), "Different seeds produced identical output"


def test_brightness_temperature_positive_correlation(df):
    """
    Sanity check: brighter fires should correlate with higher FRP.
    Pearson r should be > 0.2.
    """
    corr = df["bright_ti4"].corr(df["frp"].clip(upper=100))
    assert corr > 0.2, f"brightness–FRP correlation too low: {corr:.3f}"


def test_seasonal_variation():
    """
    Punjab/Haryana stubble-burning region (peak Oct-Nov) should produce more
    fires in an October simulation than a July simulation.
    """
    from datetime import date
    oct_df = generate_hotspots(days=5, seed=42, reference_date=date(2024, 11, 3))
    jul_df = generate_hotspots(days=5, seed=42, reference_date=date(2024, 7, 3))
    oct_punjab = len(oct_df[oct_df["state"] == "Punjab"])
    jul_punjab = len(jul_df[jul_df["state"] == "Punjab"])
    assert oct_punjab >= jul_punjab, (
        f"Expected more Punjab fires in Oct ({oct_punjab}) than Jul ({jul_punjab})"
    )


def test_acq_time_format(df):
    """acq_time should be 4-digit HHMM strings."""
    assert df["acq_time"].str.match(r"^\d{4}$").all(), "acq_time not in HHMM format"


def test_instrument_is_viirs(df):
    assert (df["instrument"] == "VIIRS").all(), "All instruments must be VIIRS"
