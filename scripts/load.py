import polars as pl
from sqlalchemy import create_engine, text

class Load:

    @staticmethod
    def get_engine(db_url:str):
        return create_engine(db_url)


    # Building Dimensions tables
    @staticmethod
    def build_dim_country(df:pl.DataFrame) ->pl.DataFrame:
        dim_country = (df.select(["country_code","country_name"])
              .unique()
              .sort("country_code")
            )
        return dim_country

    @staticmethod
    def build_dim_indicator(df:pl.DataFrame) ->pl.DataFrame:
        dim_indicator = (df.select(["indicator_code","indicator_name","unit_measure"])
                .unique()
                .sort("indicator_code")
            )
    
        return dim_indicator

    @staticmethod
    def build_dim_date(df:pl.DataFrame) ->pl.DataFrame:
        dim_date = (df.select(["year"])
                .unique()
                .sort("year")
            )
        return dim_date

    @staticmethod
    def build_dim_age(df:pl.DataFrame) ->pl.DataFrame:
        dim_age = (df.select(["age_code","age_label"])
                .unique()
                .sort("age_code")
                )
        return dim_age
    
    @staticmethod
    def build_dim_sex(df:pl.DataFrame) ->pl.DataFrame:
        dim_sex = (df.select(["sex_code","sex_label"])
                .unique()
                .sort("sex_code")
            )
        return dim_sex

    @staticmethod
    def build_dim_urbanisation(df:pl.DataFrame) ->pl.DataFrame:
        dim_urbanisation = (df.select(["urban_code","urban_label"])
                    .unique()
                    .sort("urban_code")
                )
        return dim_urbanisation\


    # loading tables

    @staticmethod
    def load_table(df:pl.DataFrame,table_name:str,engine):
        df.write_database(
            table_name=table_name,
            connection=engine,
            if_table_exists="append"
        )
        print(f"{table_name} loaded")

    @staticmethod
    def load_all(df:pl.DataFrame, engine):

        dim_country = Load.build_dim_country(df)
        dim_indicator = Load.build_dim_indicator(df)
        dim_date = Load.build_dim_date(df)
        dim_age = Load.build_dim_age(df)
        dim_sex = Load.build_dim_sex(df)
        dim_urbanisation = Load.build_dim_urbanisation(df)

        # print(type(dim_country))
        Load.load_table(dim_country,      "dim_country",      engine)
        Load.load_table(dim_indicator,    "dim_indicator",    engine)
        Load.load_table(dim_date,         "dim_date",         engine)
        Load.load_table(dim_sex,          "dim_sex",          engine)
        Load.load_table(dim_age,          "dim_age",          engine)
        Load.load_table(dim_urbanisation, "dim_urbanisation", engine)

        # fact table building
        with engine.connect() as conn:
            country_lookup = {
                r[0]: r[1] 
                for r in conn.execute(text("SELECT country_code, country_id FROM dim_country"))
                }
            indicator_lookup  = {
                r[0]: r[1] 
                for r in conn.execute(text("SELECT indicator_code, indicator_id FROM dim_indicator"))
                }
            date_lookup = {
                r[0]: r[1] 
                for r in conn.execute(text("SELECT year, date_id FROM dim_date"))
                }
            sex_lookup = {
                r[0]: r[1] 
            for r in conn.execute(text("SELECT sex_code, sex_id FROM dim_sex"))
                }
            age_lookup = {
                r[0]: r[1] 
                for r in conn.execute(text("SELECT age_code, age_id FROM dim_age"))
                }
            urban_lookup = {
                r[0]: r[1] 
                for r in conn.execute(text("SELECT urban_code, urban_id FROM dim_urbanisation"))
                }

        #Mapping lookups
        fact = df.select([
            "country_code", "indicator_code", "year",
            "sex_code", "age_code", "urban_code",
            "obs_value", "obs_status"
        ])

        fact = fact.join(
            pl.DataFrame({"country_code":list(country_lookup.keys()),"country_id":list(country_lookup.values())}),
            on="country_code",how="left"
        ).join(
            pl.DataFrame({"indicator_code":list(indicator_lookup.keys()),"indicator_id":list(indicator_lookup.values())}),
            on="indicator_code",how="left"
        ).join(
            pl.DataFrame({"year":list(date_lookup.keys()),"date_id":list(date_lookup.values())}),
            on="year",how="left"
        ).join(
            pl.DataFrame({"sex_code":list(sex_lookup.keys()),"sex_id":list(sex_lookup.values())}),
            on="sex_code",how="left"
        ).join(
            pl.DataFrame({"age_code":list(age_lookup.keys()),"age_id":list(age_lookup.values())}),
            on="age_code",how="left"
        ).join(
            pl.DataFrame({"urban_code":list(urban_lookup.keys()),"urban_id":list(urban_lookup.values())}),
            on="urban_code",how="left"
        )


        fact = fact.select([
            "country_id", "indicator_id", "date_id",
            "sex_id", "age_id", "urban_id",
            "obs_value", "obs_status"
        ])

        Load.load_table(fact, "fact_wdi_data", engine)