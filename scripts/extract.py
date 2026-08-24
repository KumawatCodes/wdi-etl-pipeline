import polars as pl
import sys
from core.logging import logger

# Required Columns (column pruning)
req_cols = [
    "REF_AREA","REF_AREA_LABEL","INDICATOR","INDICATOR_LABEL",
    "UNIT_MEASURE","TIME_PERIOD","SEX","SEX_LABEL","AGE","AGE_LABEL",
    "URBANISATION","URBANISATION_LABEL","OBS_VALUE","OBS_STATUS"
]

# Required indicators
indicat_req = [
    "WB_WDI_NY_GDP_PCAP_KD","WB_WDI_NY_GDP_MKTP_KD_ZG",
    "WB_WDI_FP_CPI_TOTL_ZG","WB_WDI_NE_TRD_GNFS_ZS",
    "WB_WDI_SP_DYN_LE00_IN","WB_WDI_SH_DYN_MORT",
    "WB_WDI_SH_STA_MMRT","WB_WDI_SH_XPD_CHEX_GD_ZS",
    "WB_WDI_SE_SEC_ENRR","WB_WDI_SE_TER_ENRR",
    "WB_WDI_IT_NET_USER_ZS","WB_WDI_IT_CEL_SETS_P2",
    "WB_WDI_SP_POP_TOTL","WB_WDI_SP_POP_GROW",
    "WB_WDI_SL_UEM_TOTL_ZS","WB_WDI_SL_TLF_CACT_ZS",
    "WB_WDI_EN_GHG_ALL_MT_CE_AR5","WB_WDI_EG_USE_PCAP_KG_OE",
    "WB_WDI_EG_ELC_ACCS_ZS","WB_WDI_EG_USE_COMM_FO_ZS"
]

class Extraction:
    @staticmethod
    def csv_extraction(file_path: str):
        logger.info(f"Starting CSV extraction: {file_path}")
        try:
            logger.info("Scanning CSV file")
            lf = pl.scan_csv(file_path)
            logger.info(f"Selecting {len(req_cols)} required columns")
            lf = lf.select(req_cols)
            logger.info(f"Filtering {len(indicat_req)} required indicators and years <= 2023")
            lf = (
                lf.filter(pl.col("INDICATOR").is_in(indicat_req))
                .filter(pl.col("TIME_PERIOD").cast(pl.Int32) <= 2023)
            )
            logger.info("Removing rows with null OBS_VALUE")
            lf = Extraction.drop_null(lf)
            logger.info("CSV extraction pipeline created successfully")
            return lf
        except Exception:
            logger.exception(f"CSV extraction failed: {file_path}")
            raise

    @staticmethod
    def drop_null(lf: pl.LazyFrame):
        logger.info("Applying OBS_VALUE null filter")
        return lf.filter(pl.col("OBS_VALUE").is_not_null())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Invalid arguments. Usage: python extract.py <file_path>")
        sys.exit(1)
    file_path = sys.argv[1]
    logger.info("Extraction job started")
    lf = Extraction.csv_extraction(file_path)
    logger.info("Executing LazyFrame")
    try:
        df = lf.collect()
        logger.info(f"Extraction completed successfully. Rows extracted: {df.height}")
    except Exception:
        logger.exception("Extraction execution failed")
        sys.exit(1)