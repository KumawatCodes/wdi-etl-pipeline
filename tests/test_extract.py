"""
Tests for etl/extract.py
Validates column filtering, null dropping, and LazyFrame construction.
"""
import polars as pl
import pytest
from etl.extract import Extraction, req_cols, indicat_req


def test_required_columns_list():
    """Ensure required columns list contains necessary SDMX fields."""
    assert "REF_AREA" in req_cols
    assert "INDICATOR" in req_cols
    assert "TIME_PERIOD" in req_cols
    assert "OBS_VALUE" in req_cols
    assert len(req_cols) == 14


def test_required_indicators_list():
    """Verify indicators list is populated with WDI indicators."""
    assert len(indicat_req) == 20
    assert "WB_WDI_NY_GDP_PCAP_KD" in indicat_req
    assert "WB_WDI_SP_POP_TOTL" in indicat_req


def test_drop_null_obs_values():
    """Verify drop_null removes rows where OBS_VALUE is null."""
    df = pl.DataFrame({
        "REF_AREA": ["IND", "USA", "BRA"],
        "OBS_VALUE": [100.5, None, 250.0]
    })
    lf = df.lazy()
    filtered_df = Extraction.drop_null(lf).collect()

    assert filtered_df.height == 2
    assert "USA" not in filtered_df["REF_AREA"].to_list()
    assert filtered_df["REF_AREA"].to_list() == ["IND", "BRA"]


def test_lazyframe_filtering_logic():
    """Verify indicator and year filter logic against simulated raw SDMX records."""
    df = pl.DataFrame({
        "REF_AREA": ["IND", "IND", "IND"],
        "REF_AREA_LABEL": ["India", "India", "India"],
        "INDICATOR": ["WB_WDI_NY_GDP_PCAP_KD", "NON_EXISTENT_IND", "WB_WDI_SP_POP_TOTL"],
        "INDICATOR_LABEL": ["GDP", "Unknown", "Population"],
        "UNIT_MEASURE": ["USD", "N/A", "Persons"],
        "TIME_PERIOD": [2020, 2020, 2026],  # 2026 exceeds threshold 2023
        "SEX": ["_T", "_T", "_T"],
        "SEX_LABEL": ["Total", "Total", "Total"],
        "AGE": ["_T", "_T", "_T"],
        "AGE_LABEL": ["Total", "Total", "Total"],
        "URBANISATION": ["_T", "_T", "_T"],
        "URBANISATION_LABEL": ["Total", "Total", "Total"],
        "OBS_VALUE": [2000.0, 50.0, 1400000000.0],
        "OBS_STATUS": ["A", "A", "A"]
    })

    lf = df.lazy()
    filtered_lf = (
        lf.select(req_cols)
        .filter(pl.col("INDICATOR").is_in(indicat_req))
        .filter(pl.col("TIME_PERIOD").cast(pl.Int32) <= 2023)
    )
    result_df = Extraction.drop_null(filtered_lf).collect()

    # Only first row should match (valid indicator AND year <= 2023)
    assert result_df.height == 1
    assert result_df["REF_AREA"][0] == "IND"
    assert result_df["TIME_PERIOD"][0] == 2020
    assert result_df["INDICATOR"][0] == "WB_WDI_NY_GDP_PCAP_KD"
