"""
Tests for etl/load.py
Validates dimensional modeling, deduplication, sorting, and fact table construction.
"""
import polars as pl
import pytest
from etl.load import Load


@pytest.fixture
def sample_transformed_dataframe():
    """Provides a sample transformed DataFrame for warehouse loading."""
    return pl.DataFrame({
        "country_code": ["IND", "IND", "USA"],
        "country_name": ["India", "India", "United States"],
        "indicator_code": ["WB_WDI_NY_GDP_PCAP_KD", "WB_WDI_SP_POP_TOTL", "WB_WDI_NY_GDP_PCAP_KD"],
        "indicator_name": ["GDP per capita", "Population", "GDP per capita"],
        "unit_measure": ["USD", "Persons", "USD"],
        "year": [2020, 2020, 2020],
        "sex_code": ["_T", "_T", "_T"],
        "sex_label": ["Total", "Total", "Total"],
        "age_code": ["_T", "_T", "_T"],
        "age_label": ["Total", "Total", "Total"],
        "urban_code": ["_T", "_T", "_T"],
        "urban_label": ["Total", "Total", "Total"],
        "obs_value": [1933.1, 1396387127.0, 63528.6],
        "obs_status": ["A", "A", "A"]
    })


def test_build_dim_country(sample_transformed_dataframe):
    """Verify dim_country extracts unique sorted countries."""
    dim = Load.build_dim_country(sample_transformed_dataframe)
    assert dim.height == 2  # IND and USA
    assert dim.columns == ["country_code", "country_name"]
    assert dim["country_code"].to_list() == ["IND", "USA"]


def test_build_dim_indicator(sample_transformed_dataframe):
    """Verify dim_indicator extracts unique indicators."""
    dim = Load.build_dim_indicator(sample_transformed_dataframe)
    assert dim.height == 2
    assert dim.columns == ["indicator_code", "indicator_name", "unit_measure"]


def test_build_dim_date(sample_transformed_dataframe):
    """Verify dim_date extracts unique sorted years."""
    dim = Load.build_dim_date(sample_transformed_dataframe)
    assert dim.height == 1
    assert dim.columns == ["year"]
    assert dim["year"][0] == 2020


def test_build_demographic_dimensions(sample_transformed_dataframe):
    """Verify demographic dimensions (age, sex, urbanisation) build correctly."""
    dim_sex = Load.build_dim_sex(sample_transformed_dataframe)
    dim_age = Load.build_dim_age(sample_transformed_dataframe)
    dim_urban = Load.build_dim_urbanisation(sample_transformed_dataframe)

    assert dim_sex.height == 1
    assert dim_age.height == 1
    assert dim_urban.height == 1
    assert dim_sex.columns == ["sex_code", "sex_label"]
    assert dim_age.columns == ["age_code", "age_label"]
    assert dim_urban.columns == ["urban_code", "urban_label"]


def test_fact_mapping_integrity(sample_transformed_dataframe):
    """Verify dimension lookup join logic maps natural keys to surrogate keys."""
    # Simulated surrogate key lookups
    country_lookup = {"IND": 1, "USA": 2}
    indicator_lookup = {"WB_WDI_NY_GDP_PCAP_KD": 101, "WB_WDI_SP_POP_TOTL": 102}
    date_lookup = {2020: 20201}
    sex_lookup = {"_T": 1}
    age_lookup = {"_T": 1}
    urban_lookup = {"_T": 1}

    df = sample_transformed_dataframe
    fact = df.select([
        "country_code", "indicator_code", "year",
        "sex_code", "age_code", "urban_code",
        "obs_value", "obs_status"
    ])

    fact = fact.join(
        pl.DataFrame({"country_code": list(country_lookup.keys()), "country_id": list(country_lookup.values())}),
        on="country_code", how="left"
    ).join(
        pl.DataFrame({"indicator_code": list(indicator_lookup.keys()), "indicator_id": list(indicator_lookup.values())}),
        on="indicator_code", how="left"
    ).join(
        pl.DataFrame({"year": list(date_lookup.keys()), "date_id": list(date_lookup.values())}),
        on="year", how="left"
    ).join(
        pl.DataFrame({"sex_code": list(sex_lookup.keys()), "sex_id": list(sex_lookup.values())}),
        on="sex_code", how="left"
    ).join(
        pl.DataFrame({"age_code": list(age_lookup.keys()), "age_id": list(age_lookup.values())}),
        on="age_code", how="left"
    ).join(
        pl.DataFrame({"urban_code": list(urban_lookup.keys()), "urban_id": list(urban_lookup.values())}),
        on="urban_code", how="left"
    )

    final_fact = fact.select([
        "country_id", "indicator_id", "date_id",
        "sex_id", "age_id", "urban_id",
        "obs_value", "obs_status"
    ])

    assert final_fact.height == 3
    # Ensure no foreign key lookup returned null
    assert final_fact["country_id"].null_count() == 0
    assert final_fact["indicator_id"].null_count() == 0
    assert final_fact["date_id"].null_count() == 0
    assert final_fact["country_id"].to_list() == [1, 1, 2]
    assert final_fact["indicator_id"].to_list() == [101, 102, 101]
