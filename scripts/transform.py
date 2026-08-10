import polars as pl
from typing import Dict

cols_rename ={
    "REF_AREA": "country_code",     
    "REF_AREA_LABEL" : "country_name",      
    "INDICATOR": "indicator_code",
    "INDICATOR_LABEL": "indicator_name",   
    "UNIT_MEASURE" : "unit_measure",    
    "TIME_PERIOD" : "year",            
    "SEX" : "sex_code",      
    "SEX_LABEL" : "sex_label",       
    "AGE" : "age_code",          
    "AGE_LABEL" : "age_label",       
    "URBANISATION" : "urban_code",      
    "URBANISATION_LABEL" : "urban_label",     
    "OBS_VALUE" : "obs_value",         
    "OBS_STATUS" : "obs_status"        
}

class Transformation:

    @staticmethod
    def transform_lf(lf:pl.LazyFrame) -> pl.DataFrame:
        lf = Transformation.rename_column(lf)
        lf = Transformation.cast_col(lf)
        return lf.collect()
    
    @staticmethod
    def rename_column(lf:pl.LazyFrame,cols_rename:Dict = cols_rename):
        lf = lf.rename(cols_rename)
        return lf

    @staticmethod
    def cast_col(lf:pl.LazyFrame):
        lf = lf.with_columns(
            pl.col("year").cast(pl.Int32),
            pl.col("obs_value").cast(pl.Float64)
        )
        return lf
    