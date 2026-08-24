from scripts.extract import Extraction
from scripts.transform import Transformation
from scripts.load import Load
from core.logging import logger

DB_URL = "postgresql+psycopg2://wdi_user:wdi_pass@localhost:5432/wdi_db"
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