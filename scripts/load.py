"""
load.py — Stage 3 of the WDI ETL pipeline (Simple Staging Table Version).

This version uses the "Staging Table" pattern.
1. Dump all cleaned chunks into a flat staging table using pandas.to_sql().
2. After all chunks are loaded, run SQL queries to populate dims and fact.
3. Drop the staging table.

All database connections are passed in explicitly from run_pipeline.py.
"""

import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_staging_table(engine):
    """Create the flat staging table. No constraints, just raw columns."""

    with engine.connect() as conn:
        conn.execute(text("""
            DROP TABLE IF EXISTS staging_wdi_raw CASCADE;
            CREATE TABLE staging_wdi_raw (
                ref_area VARCHAR(10),
                ref_area_label VARCHAR(255),
                indicator VARCHAR(50),
                indicator_label TEXT,
                sex VARCHAR(10),
                age VARCHAR(10),
                age_label VARCHAR(100),
                urbanisation VARCHAR(10),
                time_period INTEGER,
                obs_value FLOAT,
                unit_measure VARCHAR(20)
            );
        """))
        conn.commit()
        logging.info("Staging table created.")


def load_chunk(engine, df):
    """Append a cleaned chunk to the staging table."""
    if df.empty:
        return 0

    # 1. Convert all column names to lowercase to match the staging table schema
    df.columns = df.columns.str.lower()

    # 2. Define the exact columns the staging table expects
    staging_columns = [
        'ref_area', 'ref_area_label', 
        'indicator', 'indicator_label', 
        'sex', 
        'age', 'age_label', 
        'urbanisation', 
        'time_period', 
        'obs_value', 
        'unit_measure'
    ]

    # 3. Keep only the columns that exist in the DataFrame AND are in the staging table
    columns_to_load = [col for col in staging_columns if col in df.columns]
    df_to_load = df[columns_to_load]

    # 4. Insert into the staging table
    df_to_load.to_sql('staging_wdi_raw', engine, if_exists='append', index=False)
    
    logging.info(f"Loaded {len(df_to_load)} rows into staging.")
    return len(df_to_load)

def finalize_load(engine):
    """
    Run after all chunks are loaded.
    Pure SQL batch operations to populate dims and fact.
    """
    logging.info("Finalizing load with SQL batch operations...")
    
    with engine.begin() as conn:
        
        # 1. Populate Country Dimension
        conn.execute(text("""
            INSERT INTO dim_country (country_code, country_name)
            SELECT DISTINCT ref_area, ref_area_label
            FROM staging_wdi_raw
            ON CONFLICT (country_code) DO NOTHING;
        """))
        
        # 2. Populate Indicator Dimension
        conn.execute(text("""
            INSERT INTO dim_indicator (indicator_code, indicator_name, unit_measure)
            SELECT DISTINCT indicator, indicator_label, unit_measure
            FROM staging_wdi_raw
            ON CONFLICT (indicator_code) DO NOTHING;
        """))
        
        # 3. Populate Sex Dimension
        conn.execute(text("""
            INSERT INTO dim_sex (sex_code, sex_label)
            SELECT DISTINCT sex, 
                   CASE WHEN sex = '_T' THEN 'Total' WHEN sex = 'F' THEN 'Female' WHEN sex = 'M' THEN 'Male' ELSE sex END
            FROM staging_wdi_raw
            ON CONFLICT (sex_code) DO NOTHING;
        """))
        
        # 4. Populate Age Dimension
        conn.execute(text("""
            INSERT INTO dim_age (age_code, age_label)
            SELECT DISTINCT age, age_label
            FROM staging_wdi_raw
            WHERE age IS NOT NULL
            ON CONFLICT (age_code) DO NOTHING;
        """))
        
        # 5. Populate Urbanisation Dimension
        conn.execute(text("""
            INSERT INTO dim_urbanisation (urban_code, urban_label)
            SELECT DISTINCT urbanisation, 
                   CASE WHEN urbanisation = '_T' THEN 'Total' WHEN urbanisation = 'URB' THEN 'Urban' WHEN urbanisation = 'RUR' THEN 'Rural' ELSE urbanisation END
            FROM staging_wdi_raw
            ON CONFLICT (urban_code) DO NOTHING;
        """))
        
        # 6. Populate Time Dimension
        conn.execute(text("""
            INSERT INTO dim_date (year)
            SELECT DISTINCT time_period
            FROM staging_wdi_raw
            ON CONFLICT (year) DO NOTHING;
        """))

        # 7. Populate the Fact Table (FIXED: date_id, urban_id, correct column names)
        conn.execute(text("""
            INSERT INTO fact_wdi_data (
                country_id, indicator_id, date_id, sex_id, age_id, urban_id, obs_value
            )
            SELECT 
                c.country_id,
                i.indicator_id,
                d.date_id,
                s.sex_id,
                a.age_id,
                u.urban_id,
                raw.obs_value
            FROM staging_wdi_raw raw
            JOIN dim_country c ON raw.ref_area = c.country_code
            JOIN dim_indicator i ON raw.indicator = i.indicator_code
            JOIN dim_date d ON raw.time_period = d.year
            JOIN dim_sex s ON raw.sex = s.sex_code
            JOIN dim_age a ON raw.age = a.age_code
            JOIN dim_urbanisation u ON raw.urbanisation = u.urban_code
            ON CONFLICT (country_id, indicator_id, date_id, sex_id, age_id, urban_id) DO NOTHING;
        """))
        
        # 8. Drop the staging table (cleanup)
        conn.execute(text("DROP TABLE staging_wdi_raw;"))
    
    logging.info("✅ Finalization complete. Fact and Dimensions populated.")