from etl.extract import Extraction
from etl.transform import Transformation
from etl.load import Load
from core.logging import logger
import os
from dotenv import load_dotenv
# DB_URL = "postgresql+psycopg2://wdi_user:wdi_pass@localhost:5432/wdi_db"
load_dotenv()  # loads .env

# Build the correct URL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "wdi_db")
DB_USER = os.getenv("DB_USER", "wdi_user")
DB_PASS = os.getenv("DB_PASSWORD", "wdi_pass")

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
FILE_PATH = "data/raw/WB_WDI.csv"

def run():
    logger.info("Pipeline starting")
    try:
        logger.info("Extracting data")
        lazyFrame = Extraction.csv_extraction(file_path=FILE_PATH)

        logger.info("Transforming data")
        dataFrame = Transformation.transform_lf(lazyFrame)

        logger.info("Creating database engine")
        engine = Load.get_engine(DB_URL)

        logger.info("Loading data into database")
        Load.load_all(dataFrame, engine)

        logger.info("Pipeline completed successfully")
    except Exception:
        logger.exception("Pipeline failed")
        raise

if __name__ == "__main__":
    run()