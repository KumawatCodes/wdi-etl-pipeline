import polars as pl
import sys
# Required Columns(column pruning)
req_cols = [
    "REF_AREA",
    "REF_AREA_LABEL",
    "INDICATOR",
    "INDICATOR_LABEL",
    "UNIT_MEASURE",
    "TIME_PERIOD",
    "SEX",
    "SEX_LABEL",
    "AGE",
    "AGE_LABEL",
    "URBANISATION",
    "URBANISATION_LABEL",
    "OBS_VALUE",
    "OBS_STATUS",
]

# required indicator
indicat_req = [
    "WB_WDI_NY_GDP_PCAP_KD", "WB_WDI_NY_GDP_MKTP_KD_ZG",
    "WB_WDI_FP_CPI_TOTL_ZG", "WB_WDI_NE_TRD_GNFS_ZS",
    "WB_WDI_SP_DYN_LE00_IN", "WB_WDI_SH_DYN_MORT",
    "WB_WDI_SH_STA_MMRT", "WB_WDI_SH_XPD_CHEX_GD_ZS",
    "WB_WDI_SE_SEC_ENRR", "WB_WDI_SE_TER_ENRR",
    "WB_WDI_IT_NET_USER_ZS", "WB_WDI_IT_CEL_SETS_P2",
    "WB_WDI_SP_POP_TOTL", "WB_WDI_SP_POP_GROW",
    "WB_WDI_SL_UEM_TOTL_ZS", "WB_WDI_SL_TLF_CACT_ZS",
    "WB_WDI_EN_GHG_ALL_MT_CE_AR5", "WB_WDI_EG_USE_PCAP_KG_OE",
    "WB_WDI_EG_ELC_ACCS_ZS", "WB_WDI_EG_USE_COMM_FO_ZS"
]

class Extraction:

    @staticmethod
    def csv_extraction(file_path:str):

        lf = pl.scan_csv(file_path)
        lf = lf.select(req_cols)
        lf = (lf.filter(pl.col("INDICATOR").is_in(indicat_req))
                 .filter(pl.col("TIME_PERIOD").cast(pl.Int32) <= 2023))
        lf = Extraction.drop_null(lf)
        return lf

    @staticmethod
    def drop_null(lf:pl.LazyFrame):
        lf = lf.filter(
            pl.col("OBS_VALUE").is_not_null()
        )
        return lf

if __name__ == "__main__":

    if len(sys.argv) !=2:
        print("error")
        sys.exit(1)

    file_path = sys.argv[1]
    Extraction.csv_extraction(file_path)
