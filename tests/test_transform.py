"""
Tests for etl/transform.py
Validates column renaming, data type casting, and schema alignment.
"""
import polars as pl
import pytest
from etl.transform import Transformation, cols_rename


@pytest.fixture
def sample_raw_dataframe():
    """Provides a sample Polars DataFrame conforming to raw extracted schema."""
    return pl.DataFrame({
        "REF_AREA": ["IND", "USA"],
        "REF_AREA_LABEL": ["India", "United States"],
        "INDICATOR": ["WB_WDI_NY_GDP_PCAP_KD", "WB_WDI_SP_POP_TOTL"],
        "INDICATOR_LABEL": ["GDP per capita", "Population, total"],
        "UNIT_MEASURE": ["Constant 2015 US$", "Persons"],
        "TIME_PERIOD": ["2020", "2021"],  # String to test casting to Int32
        "SEX": ["_T", "_T"],
        "SEX_LABEL": ["Total", "Total"],
        "AGE": ["_T", "_T"],
        "AGE_LABEL": ["Total", "Total"],
        "URBANISATION": ["_T", "_T"],
        "URBANISATION_LABEL": ["Total", "Total"],
        "OBS_VALUE": ["1933.1", "331893745"],  # String to test casting to Float64
        "OBS_STATUS": ["A", "A"]
    })


def test_rename_column(sample_raw_dataframe):
    """Verify raw SDMX columns are renamed to warehouse naming convention."""
    lf = sample_raw_dataframe.lazy()
    renamed_lf = Transformation.rename_column(lf)
    schema = renamed_lf.collect_schema().names()

    for old_col, new_col in cols_rename.items():
        assert new_col in schema
        assert old_col not in schema


def test_cast_col(sample_raw_dataframe):
    """Verify year is cast to Int32 and obs_value is cast to Float64."""
    lf = Transformation.rename_column(sample_raw_dataframe.lazy())
    casted_df = Transformation.cast_col(lf).collect()

    assert casted_df["year"].dtype == pl.Int32
    assert casted_df["obs_value"].dtype == pl.Float64
    assert casted_df["year"][0] == 2020
    assert casted_df["obs_value"][0] == pytest.approx(1933.1)


def test_transform_lf_end_to_end(sample_raw_dataframe):
    """Verify complete transform_lf workflow produces valid collected DataFrame."""
    lf = sample_raw_dataframe.lazy()
    df = Transformation.transform_lf(lf)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df.width == 14
    assert "country_code" in df.columns
    assert "indicator_code" in df.columns
    assert "year" in df.columns
    assert "obs_value" in df.columns
    assert df["year"].dtype == pl.Int32
    assert df["obs_value"].dtype == pl.Float64
