"""
run_pipeline.py — Orchestrates the full WDI ETL pipeline.

Connects to Postgres once, then for each chunk yielded by extract.py:
  1. cleans it (clean.py)
  2. loads it (load.py)

Includes detailed timers to identify bottlenecks.
"""

import sys
import time

from sqlalchemy import create_engine

from scripts.extract import extract_chunks
from scripts.clean import clean_chunk
from scripts.load import load_chunk


# --- Database connection ---------------------------------------------
DB_USER = "postgres"
DB_PASSWORD = "admin123"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "wdi_db"

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run(csv_path: str) -> None:
    engine = create_engine(DB_URL)

    # Fail fast if database isn't reachable
    try:
        with engine.connect() as conn:
            pass
        print(f"[run_pipeline] Connected to {DB_NAME} at {DB_HOST}:{DB_PORT}")
    except Exception as e:
        print(f"[run_pipeline] Could not connect to database: {e}")
        sys.exit(1)

    # --- NEW: Create Staging Table before loading any chunks ---
    from scripts.load import create_staging_table, load_chunk, finalize_load
    create_staging_table(engine)

    start_time = time.time()
    total_rows_loaded = 0
    chunk_number = 0

    # Aggregated timers
    total_extract_time = 0.0
    total_clean_time = 0.0
    total_load_time = 0.0

    print(f"[run_pipeline] Starting pipeline on {csv_path}")
    print("=" * 80)

    for raw_chunk in extract_chunks(csv_path):
        chunk_number += 1

        # --- Clean Timer ---
        clean_start = time.perf_counter()
        cleaned_chunk = clean_chunk(raw_chunk)
        clean_end = time.perf_counter()
        clean_time = clean_end - clean_start
        total_clean_time += clean_time

        # --- Load Timer (NOW PASSING ENGINE EXPLICITLY) ---
        load_start = time.perf_counter()
        rows_loaded = load_chunk(engine, cleaned_chunk)  # <-- FIXED: Passing engine
        load_end = time.perf_counter()
        load_time = load_end - load_start
        total_load_time += load_time

        total_rows_loaded += rows_loaded

        # Print per-chunk summary
        print(f"[run_pipeline] Chunk {chunk_number}: "
              f"{len(raw_chunk)} raw -> {len(cleaned_chunk)} cleaned -> "
              f"{rows_loaded} loaded | Clean: {clean_time:.3f}s | Load: {load_time:.3f}s")

    # --- NEW: Finalize the load (populate dims, fact, drop staging) ---
    print("\n[run_pipeline] All chunks loaded. Running finalization...")
    finalize_load(engine)

    elapsed = time.time() - start_time

    # --- Final Summary ---
    print("=" * 80)
    print("\n[run_pipeline] ✅ ETL Pipeline Complete!")
    print(f"Total chunks processed: {chunk_number}")
    print(f"Total rows loaded: {total_rows_loaded}")
    print(f"Total wall time: {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
    print("\n--- Breakdown by Stage ---")
    print(f"  Total Clean Time: {total_clean_time:.2f}s ({total_clean_time/60:.2f} min)")
    print(f"  Total Load Time:  {total_load_time:.2f}s ({total_load_time/60:.2f} min)")
    print(f"  Avg Clean per Chunk: {total_clean_time/chunk_number:.3f}s")
    print(f"  Avg Load per Chunk:  {total_load_time/chunk_number:.3f}s")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_pipeline.py <path_to_csv>")
        sys.exit(1)

    run(sys.argv[1])