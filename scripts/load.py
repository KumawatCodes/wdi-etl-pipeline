import polars as pl
from sqlalchemy import create_engine, text
from core.logging import logger

class Load:
    @staticmethod
    def get_engine(db_url: str):
        logger.info("Creating database engine")
        try:
            engine = create_engine(db_url)
            logger.info("Database engine created successfully")
            return engine
        except Exception:
            logger.exception("Failed to create database engine")
            raise

    # Building Dimension Tables
    @staticmethod
    def build_dim_country(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_country")
        dim_country = (
            df.select(["country_code", "country_name"])
            .unique()
            .sort("country_code")
        )
        logger.info(f"dim_country built: {dim_country.height} rows")
        return dim_country

    @staticmethod
    def build_dim_indicator(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_indicator")
        dim_indicator = (
            df.select(["indicator_code", "indicator_name", "unit_measure"])
            .unique()
            .sort("indicator_code")
        )
        logger.info(f"dim_indicator built: {dim_indicator.height} rows")
        return dim_indicator

    @staticmethod
    def build_dim_date(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_date")
        dim_date = (
            df.select(["year"])
            .unique()
            .sort("year")
        )
        logger.info(f"dim_date built: {dim_date.height} rows")
        return dim_date

    @staticmethod
    def build_dim_age(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_age")
        dim_age = (
            df.select(["age_code", "age_label"])
            .unique()
            .sort("age_code")
        )
        logger.info(f"dim_age built: {dim_age.height} rows")
        return dim_age

    @staticmethod
    def build_dim_sex(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_sex")
        dim_sex = (
            df.select(["sex_code", "sex_label"])
            .unique()
            .sort("sex_code")
        )
        logger.info(f"dim_sex built: {dim_sex.height} rows")
        return dim_sex

    @staticmethod
    def build_dim_urbanisation(df: pl.DataFrame) -> pl.DataFrame:
        logger.info("Building dim_urbanisation")
        dim_urbanisation = (
            df.select(["urban_code", "urban_label"])
            .unique()
            .sort("urban_code")
        )
        logger.info(f"dim_urbanisation built: {dim_urbanisation.height} rows")
        return dim_urbanisation

    # Loading Tables
    @staticmethod
    def load_table(df: pl.DataFrame, table_name: str, engine):
        logger.info(f"Loading table: {table_name} ({df.height} rows)")
        try:
            df.write_database(
                table_name=table_name,
                connection=engine,
                if_table_exists="append"
            )
            logger.info(f"{table_name} loaded successfully")
        except Exception:
            logger.exception(f"Failed to load table: {table_name}")
            raise

    @staticmethod
    def load_all(df: pl.DataFrame, engine):
        logger.info("Starting complete database load")

        try:
            # Build dimension tables
            logger.info("Building dimension tables")

            dim_country = Load.build_dim_country(df)
            dim_indicator = Load.build_dim_indicator(df)
            dim_date = Load.build_dim_date(df)
            dim_age = Load.build_dim_age(df)
            dim_sex = Load.build_dim_sex(df)
            dim_urbanisation = Load.build_dim_urbanisation(df)

            # Load dimension tables
            logger.info("Loading dimension tables")

            Load.load_table(dim_country, "dim_country", engine)
            Load.load_table(dim_indicator, "dim_indicator", engine)
            Load.load_table(dim_date, "dim_date", engine)
            Load.load_table(dim_sex, "dim_sex", engine)
            Load.load_table(dim_age, "dim_age", engine)
            Load.load_table(dim_urbanisation, "dim_urbanisation", engine)

            logger.info("All dimension tables loaded successfully")

            # Build lookup dictionaries
            logger.info("Creating dimension lookup dictionaries")

            with engine.connect() as conn:
                country_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT country_code, country_id FROM dim_country")
                    )
                }

                indicator_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT indicator_code, indicator_id FROM dim_indicator")
                    )
                }

                date_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT year, date_id FROM dim_date")
                    )
                }

                sex_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT sex_code, sex_id FROM dim_sex")
                    )
                }

                age_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT age_code, age_id FROM dim_age")
                    )
                }

                urban_lookup = {
                    r[0]: r[1]
                    for r in conn.execute(
                        text("SELECT urban_code, urban_id FROM dim_urbanisation")
                    )
                }

            logger.info("Dimension lookups created successfully")

            # Build fact table
            logger.info("Building fact table")

            fact = df.select([
                "country_code",
                "indicator_code",
                "year",
                "sex_code",
                "age_code",
                "urban_code",
                "obs_value",
                "obs_status"
            ])

            logger.info("Mapping dimension IDs to fact table")

            fact = fact.join(
                pl.DataFrame({
                    "country_code": list(country_lookup.keys()),
                    "country_id": list(country_lookup.values())
                }),
                on="country_code",
                how="left"
            ).join(
                pl.DataFrame({
                    "indicator_code": list(indicator_lookup.keys()),
                    "indicator_id": list(indicator_lookup.values())
                }),
                on="indicator_code",
                how="left"
            ).join(
                pl.DataFrame({
                    "year": list(date_lookup.keys()),
                    "date_id": list(date_lookup.values())
                }),
                on="year",
                how="left"
            ).join(
                pl.DataFrame({
                    "sex_code": list(sex_lookup.keys()),
                    "sex_id": list(sex_lookup.values())
                }),
                on="sex_code",
                how="left"
            ).join(
                pl.DataFrame({
                    "age_code": list(age_lookup.keys()),
                    "age_id": list(age_lookup.values())
                }),
                on="age_code",
                how="left"
            ).join(
                pl.DataFrame({
                    "urban_code": list(urban_lookup.keys()),
                    "urban_id": list(urban_lookup.values())
                }),
                on="urban_code",
                how="left"
            )

            logger.info("Dimension IDs mapped successfully")

            fact = fact.select([
                "country_id",
                "indicator_id",
                "date_id",
                "sex_id",
                "age_id",
                "urban_id",
                "obs_value",
                "obs_status"
            ])

            logger.info(f"Fact table prepared: {fact.height} rows")

            # Load fact table
            Load.load_table(
                fact,
                "fact_wdi_data",
                engine
            )

            logger.info("Complete database load finished successfully")

        except Exception:
            logger.exception("Database load failed")
            raise