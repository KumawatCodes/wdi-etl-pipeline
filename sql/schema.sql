-- ============================================================
-- WDI ETL Pipeline — Star Schema
-- 5 dimension tables + 1 fact table
-- See docs/DATA_DICTIONARY.md and docs/diagrams/star-schema.png
-- for the full design rationale.
-- ============================================================

-- Drop in dependency order (fact first) so this script is re-runnable
-- during developement without manual cleanup

DROP TABLE IF EXISTS fact_wdi_data;
DROP TABLE IF EXISTS dim_country;
DROP TABLE IF EXISTS dim_indicator;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_sex;
DROP TABLE IF EXISTS dim_age;
DROP TABLE IF EXISTS dim_urbanisation;

-- ------------------------------------------------------------
-- Dimension tables
-- ------------------------------------------------------------

CREATE TABLE dim_country (
    country_id   SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL UNIQUE,   -- e.g. 'IND'
    country_name VARCHAR(150) NOT NULL          -- e.g. 'India'
);

CREATE TABLE dim_indicator (
    indicator_id   SERIAL PRIMARY KEY,
    indicator_code VARCHAR(50) NOT NULL UNIQUE, -- e.g. 'NY.GDP.PCAP.KD'
    indicator_name VARCHAR(255) NOT NULL,
    unit_measure   VARCHAR(100)                 -- nullable: not every indicator has one
);

CREATE TABLE dim_date (
    date_id SERIAL PRIMARY KEY,
    year    INT NOT NULL UNIQUE                 -- e.g. 2020
);

CREATE TABLE dim_sex (
    sex_id    SERIAL PRIMARY KEY,
    sex_code  VARCHAR(10) NOT NULL UNIQUE,       -- '_T' / 'M' / 'F'
    sex_label VARCHAR(50) NOT NULL
);

CREATE TABLE dim_age (
    age_id    SERIAL PRIMARY KEY,
    age_code  VARCHAR(20) NOT NULL UNIQUE,       -- '_T' / 'Y15T24' / etc.
    age_label VARCHAR(100) NOT NULL
);

CREATE TABLE dim_urbanisation (
    urban_id    SERIAL PRIMARY KEY,
    urban_code  VARCHAR(10) NOT NULL UNIQUE,     -- '_T' / 'RUR' / 'URB'
    urban_label VARCHAR(50) NOT NULL
);

-- ------------------------------------------------------------
-- Fact table
-- ------------------------------------------------------------
-- Grain: one row = one (country, indicator, year, sex, age, urbanisation)
-- combination. A "simple" lookup like "India's GDP per capita in 2020"
-- returns MULTIPLE rows unless filtered to the Total code on sex/age/urban.
-- See docs/DESIGN.md for the full grain explanation.

CREATE TABLE fact_wdi_data (
    fact_id      BIGSERIAL PRIMARY KEY,
    country_id   INT NOT NULL REFERENCES dim_country(country_id),
    indicator_id INT NOT NULL REFERENCES dim_indicator(indicator_id),
    date_id      INT NOT NULL REFERENCES dim_date(date_id),
    sex_id       INT NOT NULL REFERENCES dim_sex(sex_id),
    age_id       INT NOT NULL REFERENCES dim_age(age_id),
    urban_id     INT NOT NULL REFERENCES dim_urbanisation(urban_id),
    obs_value    NUMERIC,                        -- nullable: clean.py drops most nulls, but
                                                   -- keep nullable here as a safety net, not a guarantee
    obs_status   VARCHAR(5),                      -- kept per team decision: cardinality check
                                                   -- sampled ~1.1% of rows; flag preserved in case
                                                   -- the full load reveals non-'A' values
    -- Prevents true duplicate observations (same combination loaded twice)
    UNIQUE (country_id, indicator_id, date_id, sex_id, age_id, urban_id)
);

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------
-- Postgres auto-indexes primary keys and UNIQUE constraints, so dimension
-- lookups by code (e.g. WHERE country_code = 'IND') are already fast.
-- These additional indexes speed up the fact table's most common access
-- patterns: filtering by one dimension, or joining on FKs.

CREATE INDEX idx_fact_country   ON fact_wdi_data(country_id);
CREATE INDEX idx_fact_indicator ON fact_wdi_data(indicator_id);
CREATE INDEX idx_fact_date      ON fact_wdi_data(date_id);

-- Composite index for the most common analytical query shape:
-- "this country, this indicator, over time" (the NGO use case)
CREATE INDEX idx_fact_country_indicator_date
    ON fact_wdi_data(country_id, indicator_id, date_id);