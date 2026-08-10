import os
from scripts.extract import Extraction
from scripts.transform import Transformation
from scripts.load import Load

DB_URL = "postgresql+psycopg2://wdi_user:wdi_pass@localhost:5432/wdi_db"
FILE_PATH = "data/raw/WB_WDI.csv"

def run():
    print(f">>> Pipeline Starting.....")

    print(f">>> Extractiong Data...")
    lazyFrame = Extraction.csv_extraction(file_path=FILE_PATH)
    print(f">>> Transforming Data...")
    dataFrame = Transformation.transform_lf(lazyFrame)
    print(f">>> Creating Engine...")
    engine = Load.get_engine(DB_URL)
    print(f">>> Loading Data Into Database...")
    Load.load_all(dataFrame,engine)

    print(f">>> Pipeline Complete")


if __name__ == "__main__":
    run()