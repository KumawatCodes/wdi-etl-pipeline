import polars as pl
from typing import Dict
from core.logging import logger

cols_rename = {
    "REF_AREA": "country_code",
    "REF_AREA_LABEL": "country_name",
    "INDICATOR": "indicator_code",
    "INDICATOR_LABEL": "indicator_name",
    "UNIT_MEASURE": "unit_measure",
    "TIME_PERIOD": "year",
    "SEX": "sex_code",
    "SEX_LABEL": "sex_label",
    "AGE": "age_code",
    "AGE_LABEL": "age_label",
    "URBANISATION": "urban_code",
    "URBANISATION_LABEL": "urban_label",
    "OBS_VALUE": "obs_value",
    "OBS_STATUS": "obs_status"
}

class Transformation:
    @staticmethod
    def transform_lf(lf: pl.LazyFrame) -> pl.DataFrame:
        logger.info("Starting transformation")
        try:
            logger.info("Renaming columns")
            lf = Transformation.rename_column(lf)
            logger.info("Casting columns")
            lf = Transformation.cast_col(lf)
            logger.info("Executing transformation")
            df = lf.collect()
            logger.info(f"Transformation completed successfully. Rows: {df.height}, Columns: {df.width}")
            return df
        except Exception:
            logger.exception("Transformation failed")
            raise

    @staticmethod
    def rename_column(lf: pl.LazyFrame, cols_rename: Dict = cols_rename):
        logger.info(f"Renaming {len(cols_rename)} columns")
        return lf.rename(cols_rename)

    @staticmethod
    def cast_col(lf: pl.LazyFrame):
        logger.info("Casting year to Int32 and obs_value to Float64")
        return lf.with_columns(
            pl.col("year").cast(pl.Int32),
            pl.col("obs_value").cast(pl.Float64)
        )