DROP TABLE IF EXISTS fact_wdi_data;
DROP TABLE IF EXISTS dim_country;
DROP TABLE IF EXISTS dim_indicator;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_sex;
DROP TABLE IF EXISTS dim_age;
DROP TABLE IF EXISTS dim_urbanisation;

CREATE TABLE dim_country (
    country_id   SERIAL PRIMARY KEY,
    country_code VARCHAR(10)  NOT NULL UNIQUE,
    country_name VARCHAR(150) NOT NULL
);

CREATE TABLE dim_indicator (
    indicator_id   SERIAL PRIMARY KEY,
    indicator_code VARCHAR(50)  NOT NULL UNIQUE,
    indicator_name VARCHAR(255) NOT NULL,
    unit_measure   VARCHAR(100)
);

CREATE TABLE dim_date (
    date_id SERIAL PRIMARY KEY,
    year    INT NOT NULL UNIQUE
);

CREATE TABLE dim_sex (
    sex_id    SERIAL PRIMARY KEY,
    sex_code  VARCHAR(10) NOT NULL UNIQUE,
    sex_label VARCHAR(50) NOT NULL
);

CREATE TABLE dim_age (
    age_id    SERIAL PRIMARY KEY,
    age_code  VARCHAR(20) NOT NULL UNIQUE,
    age_label VARCHAR(100) NOT NULL
);

CREATE TABLE dim_urbanisation (
    urban_id    SERIAL PRIMARY KEY,
    urban_code  VARCHAR(10) NOT NULL UNIQUE,
    urban_label VARCHAR(50) NOT NULL
);

CREATE TABLE fact_wdi_data (
    fact_id      BIGSERIAL PRIMARY KEY,
    country_id   INT NOT NULL REFERENCES dim_country(country_id),
    indicator_id INT NOT NULL REFERENCES dim_indicator(indicator_id),
    date_id      INT NOT NULL REFERENCES dim_date(date_id),
    sex_id       INT NOT NULL REFERENCES dim_sex(sex_id),
    age_id       INT NOT NULL REFERENCES dim_age(age_id),
    urban_id     INT NOT NULL REFERENCES dim_urbanisation(urban_id),
    obs_value    NUMERIC,
    obs_status   VARCHAR(5),
    UNIQUE (country_id, indicator_id, date_id, sex_id, age_id, urban_id)
);

CREATE INDEX idx_fact_country_indicator_date
    ON fact_wdi_data(country_id, indicator_id, date_id);