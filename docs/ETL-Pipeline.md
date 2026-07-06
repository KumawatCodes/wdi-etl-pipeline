## 1. Overview

### 1.1 Executive Summary

The WDI ETL Pipeline is a production-grade data engineering solution designed to ingest, transform, and load World Development Indicators data from the World Bank into a PostgreSQL Star Schema. The pipeline processes a **3.6GB CSV file containing 8.9 million rows and 41 columns** on resource-constrained local development machines (8-16GB RAM).

The core architectural innovation is a **Streaming (Chunked) Architecture** combined with a **Staging Table Pattern**, enabling the pipeline to process datasets that exceed available system memory without triggering Out-of-Memory (OOM) failures.

### 1.2 The Problem Statement

#### Why Naive Loading Fails

A standard approach to CSV ingestion in Python uses Pandas:

df = pd.read_csv("WB_WDI.csv")  # DO NOT DO THIS

This single line of code attempts to load the **entire 3.6GB file into RAM simultaneously**. Due to Pandas' internal data structures (Python object overhead, index allocation, type inference buffers), the actual memory footprint expands to approximately **3-5x the file size on disk**—potentially consuming 10-18GB of RAM.

On a machine with 8-16GB of total system memory, this triggers the following failure cascade:

1. **Memory Exhaustion:** Python's process memory grows beyond available RAM.
    
2. **Swap Thrashing:** The OS begins swapping to disk, causing severe performance degradation.
    
3. **OOM Killer Invocation:** The Linux kernel's Out-of-Memory Killer terminates the Python process to protect system stability.
    

**Result:** The pipeline crashes before any meaningful work begins.

#### The Solution: Streaming Architecture

The WDI ETL Pipeline solves this constraint through a **Streaming (Chunked) Architecture**:

- The 3.6GB file is never loaded entirely into memory.
    
- Instead, the file is read in **discrete chunks of 100,000 rows** each.
    
- Each chunk is processed independently: extracted, cleaned, and loaded into the database.
    
- Once a chunk is persisted to PostgreSQL, Python's garbage collector reclaims the memory.
    
- The disk (via PostgreSQL) serves as the intermediate buffer, not Python RAM.
    

This approach reduces peak memory consumption from **10-18GB to approximately 200-400MB**, making the pipeline viable on standard development hardware.

---

## 2. Goals and Non-Goals

### 2.1 Goals

|Goal<br><br>+<br><br>+<br><br>+|Description<br><br>+|
|---|---|
|**Memory Safety**<br><br>+|Process the full 8.9M-row dataset without exceeding 1GB of Python heap memory.|
|**Data Integrity**<br><br>+|Ensure all rows are loaded without duplication or data loss via the Staging Table Pattern.|
|**Schema Compliance**<br><br>+|Produce a normalized Star Schema with proper foreign key relationships.|
|**Reproducibility**<br><br>+|Enable idempotent re-runs via staging table truncation and batch finalization.|
|**Observability**<br><br>+|Provide logging at each stage for debugging and performance monitoring.|

### 2.2 Non-Goals

|Non-Goal<br><br>+<br><br>+<br><br>+|Rationale<br><br>+|
|---|---|
|**Real-Time Streaming**<br><br>+|This is a batch ETL pipeline; sub-second latency is not required.|
|**Distributed Processing**<br><br>+|The pipeline targets single-node execution; Spark/Dask integration is out of scope.|
|**Incremental Loading**<br><br>+|Each run processes the full dataset; CDC (Change Data Capture) is not implemented.|
|**Cloud Deployment**<br><br>+|The pipeline is designed for local Docker-based PostgreSQL; cloud migration is a future enhancement.|

---

## 3. Architecture

### 3.1 High-Level Architecture Diagram

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           WDI ETL PIPELINE - STREAMING ARCHITECTURE             │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
  │    SOURCE    │      │   EXTRACT    │      │    CLEAN     │      │     LOAD     │
  │              │      │              │      │              │      │   (Staging)  │
  │  WB_WDI.csv  │─────▶│  extract.py  │─────▶│   clean.py   │─────▶│   load.py    │
  │   3.6GB      │      │  (Generator) │      │ (Transform)  │      │  (Insert)    │
  │   8.9M rows  │      │              │      │              │      │              │
  │   41 cols    │      │  yields 100k │      │  per-chunk   │      │  staging_    │
  │              │      │  row chunks  │      │  operations  │      │  wdi_raw     │
  └──────────────┘      └──────────────┘      └──────────────┘      └──────┬───────┘
                                                                          │
                        ◀───────────────────────────────────────────────────
                                    STREAMING LOOP (~89 iterations)
                                                                          │
                                                                          ▼
                                                               ┌──────────────────┐
                                                               │   FINALIZATION   │
                                                               │                  │
                                                               │  Batch SQL:      │
                                                               │  • Populate dims │
                                                               │  • Resolve FKs   │
                                                               │  • Load fact     │
                                                               │                  │
                                                               │  ┌────────────┐  │
                                                               │  │ Star       │  │
                                                               │  │ Schema     │  │
                                                               │  │ (Final)    │  │
                                                               │  └────────────┘  │
                                                               └──────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────────────┐
  │  MEMORY FOOTPRINT: Only ONE chunk (~100k rows) in Python memory at any time.   │
  │  Peak RAM usage: ~200-400MB (vs. 10-18GB for naive full-file load).            │
  └─────────────────────────────────────────────────────────────────────────────────┘

### 3.2 Component Breakdown

#### Stage 1: Extraction (`extract.py`)

**Purpose:** Read the source CSV file incrementally without loading the entire dataset into memory.

**Key Mechanism: Python Generators and the** `**yield**` **Keyword**

The extraction module implements a **Generator Function**—a special type of Python function that uses the `yield` keyword instead of `return`. Unlike a regular function that computes its entire result before returning, a generator produces values **lazily, one at a time, on demand**.

def extract_chunks(filepath: str, chunksize: int = 100_000):
    """
    Generator that yields DataFrames of `chunksize` rows.
    The file is never fully loaded into memory.
    """
    for chunk in pd.read_csv(filepath, chunksize=chunksize):
        # Prune unnecessary columns immediately
        chunk = chunk.drop(columns=SDMX_PLUMBING_COLUMNS, errors='ignore')
        yield chunk

**Why This Matters:**

- When the caller iterates over `extract_chunks()` , Pandas reads **only the next 100,000 rows** from disk.
    
- The generator **pauses execution** at the `yield` statement, returning control to the caller.
    
- When the caller requests the next chunk, the generator **resumes from where it paused**.
    
- This "lazy evaluation" pattern means the file pointer advances incrementally; the full 3.6GB file is never resident in memory.
    

**Column Pruning:**

The source CSV contains 41 columns, but 27 of these are **SDMX plumbing columns**—metadata fields used by the World Bank's data exchange format that carry no analytical value (e.g., `STRUCTURE`, `STRUCTURE_ID`, `ACTION`). These columns are **dropped immediately upon extraction** to reduce the per-chunk memory footprint from 41 columns to 14 columns.

**Output:** A generator yielding DataFrames of ~100,000 rows × 14 columns each.

---

#### Stage 2: Cleaning (`clean.py`)

**Purpose:** Transform each chunk into a clean, analysis-ready format.

**Key Constraint: Per-Chunk Isolation**

The cleaning module operates on **one chunk at a time**. It has no visibility into previous or subsequent chunks. This isolation is intentional—it preserves the memory-safe streaming guarantee—but it introduces a limitation:

> **Global deduplication is impossible at this stage.** If duplicate rows span multiple chunks, the cleaning module cannot detect or remove them.

This limitation is addressed later via the **Staging Table Pattern** (see Stage 4).

**Transformations Applied:**

|Transformation<br><br>+<br><br>+<br><br>+|Description<br><br>+|Example<br><br>+|
|---|---|---|
|**CODE/LABEL Collapse**<br><br>+|The source data contains redundant column pairs (e.g., `COUNTRY_CODE` and `COUNTRY_LABEL`). We retain only the CODE column to reduce width.|`COUNTRY_CODE: "USA"` retained; `COUNTRY_LABEL: "United States"` dropped.|
|**AGE Code Parsing**<br><br>+|Age demographic codes are stored in SDMX format (e.g., `Y15T24`). A vectorized regex operation parses these into human-readable labels.|`Y15T24` → `"15 to 24 years"`|
|**NULL Value Filtering**<br><br>+|Rows where `OBS_VALUE` (the observation/measurement value) is NULL carry no analytical meaning and are dropped.|Rows with `OBS_VALUE = NaN` removed.|

**Implementation Note:** All transformations use **vectorized Pandas operations** (not Python `for` loops) to maximize throughput. Vectorized operations leverage NumPy's C-based backend, processing millions of cells in milliseconds.

**Output:** A cleaned DataFrame of ~100,000 rows × ~10 columns, ready for staging.

---

#### Stage 3: Loading to Staging (`load.py` - Streaming Phase)

**Purpose:** Persist each cleaned chunk to a PostgreSQL staging table as quickly as possible.

**The Staging Table:** `**staging_wdi_raw**`

The staging table is a **flat, denormalized, append-only table** with the following characteristics:

|Property<br><br>+<br><br>+<br><br>+|Value<br><br>+|Rationale<br><br>+|
|---|---|---|
|**Schema**<br><br>+|Mirrors the cleaned chunk structure (no foreign keys).|Eliminates JOIN overhead during inserts.|
|**Indexes**<br><br>+|None (or minimal).|Speeds up bulk INSERT operations.|
|**Constraints**<br><br>+|None (no PRIMARY KEY, no UNIQUE).|Allows duplicates temporarily; dedup happens later.|

**Why No Foreign Key Resolution Here?**

Resolving foreign keys during the streaming loop would require:

1. Querying dimension tables to look up surrogate keys.
    
2. Performing JOIN operations for every chunk.
    
3. Potentially inserting new dimension records on-the-fly.
    

These operations are **expensive** and would slow the streaming loop significantly. By deferring FK resolution to the finalization phase, we keep the streaming loop **as fast as possible**: each chunk is a simple bulk INSERT with no dependencies.

**Insert Mechanism:**

chunk.to_sql(
    name='staging_wdi_raw',
    con=engine,
    if_exists='append',
    index=False,
    method='multi'  # Batch INSERT for performance
)

**Output:** The staging table accumulates all 8.9 million rows across ~89 chunk inserts.

---

#### Stage 4: Finalization (`load.py` - Batch SQL Phase)

**Purpose:** Transform the flat staging table into a normalized Star Schema with proper foreign key relationships.

**The Staging Table Pattern**

The **Staging Table Pattern** is a classic data warehousing technique:

1. **Load Phase:** Rapidly ingest raw data into a temporary staging area without transformation.
    
2. **Transform Phase:** Use the database engine's native SQL capabilities to clean, deduplicate, and normalize the data.
    
3. **Publish Phase:** Move the transformed data into the final production tables.
    

This pattern leverages the database's **set-based processing engine**, which is highly optimized for operations like `DISTINCT`, `GROUP BY`, and `JOIN` across millions of rows.

**Finalization Operations:**

**Step 1: Populate Dimension Tables**

Dimension tables (`dim_country`, `dim_indicator`, `dim_date`, `dim_age`, etc.) are populated using `INSERT ... SELECT DISTINCT` queries:

INSERT INTO dim_country (country_code, country_name)
SELECT DISTINCT country_code, country_name
FROM staging_wdi_raw
WHERE country_code NOT IN (SELECT country_code FROM dim_country);

This query:

- Extracts all unique country values from the staging table.
    
- Filters out any countries that already exist in the dimension (idempotency).
    
- Inserts only net-new dimension members.
    

**Step 2: Populate the Fact Table**

The fact table (`fact_wdi_data`) is populated by joining the staging table with all dimension tables to resolve surrogate foreign keys:

INSERT INTO fact_wdi_data (
    country_id, indicator_id, date_id, age_id, obs_value
)
SELECT 
    dc.country_id,
    di.indicator_id,
    dd.date_id,
    da.age_id,
    s.obs_value
FROM staging_wdi_raw s
JOIN dim_country dc ON s.country_code = dc.country_code
JOIN dim_indicator di ON s.indicator_code = di.indicator_code
JOIN dim_date dd ON s.time_period = dd.time_period
JOIN dim_age da ON s.age_code = da.age_code;

This single SQL statement:

- Joins the 8.9M-row staging table with all dimension tables.
    
- Resolves natural keys (e.g., `country_code` ) to surrogate keys (e.g., `country_id` ).
    
- Inserts the fully normalized fact records.
    

**Why This Is Fast:**

PostgreSQL's query planner optimizes these operations using:

- **Hash Joins:** Efficient for large table joins.
    
- **Parallel Query Execution:** Utilizes multiple CPU cores.
    
- **Disk-Based Sorting:** Handles datasets larger than RAM via external merge sort.
    

**Output:** A fully normalized Star Schema ready for analytical queries.

---

## 4. Data Model

### 4.1 Staging Schema

┌─────────────────────────────────────┐
│         staging_wdi_raw             │
├─────────────────────────────────────┤
│ country_code       VARCHAR(10)      │
│ country_name       VARCHAR(255)     │
│ indicator_code     VARCHAR(50)      │
│ indicator_name     VARCHAR(500)     │
│ time_period        INTEGER          │
│ age_code           VARCHAR(20)      │
│ age_label          VARCHAR(100)     │
│ sex_code           VARCHAR(10)      │
│ obs_value          DECIMAL(18,6)    │
│ unit_measure       VARCHAR(50)      │
│ ... (additional columns)            │
└─────────────────────────────────────┘
        │
        │ FINALIZATION (Batch SQL)
        ▼
┌─────────────────────────────────────────────────────────────────┐
│                         STAR SCHEMA                             │
└─────────────────────────────────────────────────────────────────┘

### 4.2 Star Schema (Final)

                    ┌─────────────────┐
                    │   dim_country   │
                    ├─────────────────┤
                    │ country_id (PK) │
                    │ country_code    │
                    │ country_name    │
                    └────────┬────────┘
                             │
┌─────────────────┐          │          ┌─────────────────┐
│  dim_indicator  │          │          │    dim_date     │
├─────────────────┤          │          ├─────────────────┤
│ indicator_id(PK)│          │          │ date_id (PK)    │
│ indicator_code  │          │          │ time_period     │
│ indicator_name  │          │          │ year            │
└────────┬────────┘          │          └────────┬────────┘
         │                   │                   │
         │         ┌─────────┴─────────┐         │
         │         │   fact_wdi_data   │         │
         │         ├───────────────────┤         │
         └────────▶│ country_id (FK)   │◀────────┘
                   │ indicator_id (FK) │
         ┌────────▶│ date_id (FK)      │◀────────┐
         │         │ age_id (FK)       │         │
         │         │ sex_id (FK)       │         │
         │         │ obs_value         │         │
         │         │ unit_measure      │         │
         │         └───────────────────┘         │
         │                                       │
┌────────┴────────┐                   ┌──────────┴──────┐
│    dim_age      │                   │    dim_sex      │
├─────────────────┤                   ├─────────────────┤
│ age_id (PK)     │                   │ sex_id (PK)     │
│ age_code        │                   │ sex_code        │
│ age_label       │                   │ sex_label       │
└─────────────────┘                   └─────────────────┘

---

## 5. API Design

### 5.1 Module Interfaces

#### `extract.py`

def extract_chunks(
    filepath: str,
    chunksize: int = 100_000,
    columns_to_drop: List[str] = SDMX_PLUMBING_COLUMNS
) -> Generator[pd.DataFrame, None, None]:
    """
    Yields cleaned DataFrames of `chunksize` rows from the source CSV.
    
    Args:
        filepath: Path to the source CSV file.
        chunksize: Number of rows per chunk (default: 100,000).
        columns_to_drop: List of column names to prune immediately.
    
    Yields:
        pd.DataFrame: A chunk of cleaned source data.
    """

#### `clean.py`

def clean_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """
    Applies all cleaning transformations to a single chunk.
    
    Args:
        chunk: A raw DataFrame from the extraction stage.
    
    Returns:
        pd.DataFrame: A cleaned DataFrame ready for staging.
    """

#### `load.py`

def load_chunk_to_staging(chunk: pd.DataFrame, engine: Engine) -> int:
    """
    Inserts a cleaned chunk into the staging table.
    
    Args:
        chunk: A cleaned DataFrame from the cleaning stage.
        engine: SQLAlchemy engine connected to PostgreSQL.
    
    Returns:
        int: Number of rows inserted.
    """

def finalize_star_schema(engine: Engine) -> Dict[str, int]:
    """
    Executes batch SQL to populate dimension and fact tables.
    
    Args:
        engine: SQLAlchemy engine connected to PostgreSQL.
    
    Returns:
        Dict[str, int]: Row counts for each table populated.
    """

### 5.2 Orchestration (`main.py`)

def run_pipeline():
    """Main entry point for the ETL pipeline."""
    
    engine = create_engine(DATABASE_URL)
    
    # Phase 1: Streaming Loop
    for chunk in extract_chunks(SOURCE_FILE):
        cleaned = clean_chunk(chunk)
        load_chunk_to_staging(cleaned, engine)
    
    # Phase 2: Batch Finalization
    finalize_star_schema(engine)

---

## 6. Security Considerations

### 6.1 Data Security

|Concern<br><br>+<br><br>+<br><br>+|Mitigation<br><br>+|
|---|---|
|**Sensitive Data Exposure**<br><br>+|The WDI dataset is publicly available; no PII is present.|
|**SQL Injection**<br><br>+|All database operations use parameterized queries via SQLAlchemy ORM.|
|**Credential Management**<br><br>+|Database credentials are stored in environment variables, not hardcoded.|

### 6.2 Infrastructure Security

|Concern<br><br>+<br><br>+<br><br>+|Mitigation<br><br>+|
|---|---|
|**Database Access**<br><br>+|PostgreSQL runs in an isolated Docker container with no external port exposure.|
|**File System Access**<br><br>+|The pipeline reads only from a designated `data/` directory.|

---

## 7. Memory Management

### 7.1 The Core Guarantee

> **Only ONE chunk (~100,000 rows) is held in Python memory at any given moment.**

This is the foundational architectural guarantee that enables the pipeline to process datasets exceeding available RAM.

### 7.2 Memory Lifecycle

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MEMORY LIFECYCLE PER ITERATION                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. EXTRACT: Generator yields chunk N (100k rows loaded into RAM)           │
│                         ↓                                                   │
│  2. CLEAN: Chunk N transformed in-place (same memory, modified)             │
│                         ↓                                                   │
│  3. LOAD: Chunk N serialized to PostgreSQL (data copied to disk)            │
│                         ↓                                                   │
│  4. LOOP: Python moves to next iteration                                    │
│           - Reference to chunk N is released                                │
│           - Garbage collector reclaims chunk N's memory                     │
│           - Generator yields chunk N+1 (new 100k rows loaded)               │
│                                                                             │
│  RESULT: Peak memory never exceeds ~1 chunk + overhead (~200-400MB)         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

### 7.3 Disk as the Buffer

In a naive implementation, Python RAM would serve as the buffer between extraction and final loading. This is untenable for large datasets.

In the streaming architecture, **PostgreSQL's staging table serves as the buffer**:

- Each chunk is immediately persisted to disk (PostgreSQL's data files).
    
- The database handles buffering, caching, and overflow to disk transparently.
    
- Python's role is reduced to **orchestration and transformation**, not storage.
    

This inversion—using disk (database) as the buffer instead of RAM—is the key insight that enables processing of arbitrarily large datasets on fixed-memory machines.

---

## 8. Testing Strategy

### 8.1 Unit Tests

|Module<br><br>+<br><br>+<br><br>+|Test Cases<br><br>+|
|---|---|
|`extract.py`<br><br>+|Verify generator yields correct chunk sizes; verify column pruning.|
|`clean.py`<br><br>+|Verify AGE code parsing; verify NULL filtering; verify CODE/LABEL collapse.|
|`load.py`<br><br>+|Verify staging insert row counts; verify finalization SQL correctness.|

### 8.2 Integration Tests

|Test<br><br>+<br><br>+<br><br>+|Description<br><br>+|
|---|---|
|**End-to-End Small File**<br><br>+|Run full pipeline on a 10,000-row sample; verify Star Schema integrity.|
|**Memory Profiling**<br><br>+|Run full pipeline with `memory_profiler`; verify peak RAM < 500MB.|
|**Idempotency**<br><br>+|Run pipeline twice; verify no duplicate records in final tables.|

### 8.3 Data Quality Tests

|Test<br><br>+<br><br>+<br><br>+|Description<br><br>+|
|---|---|
|**Row Count Reconciliation**<br><br>+|Verify `SUM(staging rows) == SUM(fact rows) + filtered NULLs`.|
|**Referential Integrity**<br><br>+|Verify all fact table FKs resolve to valid dimension records.|
|**Value Range Checks**<br><br>+|Verify `obs_value` falls within expected bounds per indicator.|

---

## 9. Rollout Plan

### 9.1 Phase 1: Local Development

|Step<br><br>+<br><br>+<br><br>+|Action<br><br>+|
|---|---|
|1<br><br>+|Provision PostgreSQL via Docker Compose.|
|2<br><br>+|Run schema migrations to create staging and Star Schema tables.|
|3<br><br>+|Execute pipeline against full 3.6GB dataset.|
|4<br><br>+|Validate output via SQL queries and data quality checks.|

### 9.2 Phase 2: CI/CD Integration

|Step<br><br>+<br><br>+<br><br>+|Action<br><br>+|
|---|---|
|1<br><br>+|Add unit tests to CI pipeline (GitHub Actions).|
|2<br><br>+|Add integration tests using a sample dataset.|
|3<br><br>+|Add memory profiling gate (fail if peak RAM > 1GB).|

### 9.3 Phase 3: Production Hardening (Future)

|Step<br><br>+<br><br>+<br><br>+|Action<br><br>+|
|---|---|
|1<br><br>+|Migrate PostgreSQL to managed cloud instance (e.g., AWS RDS).|
|2<br><br>+|Add Airflow DAG for scheduled execution.|
|3<br><br>+|Add monitoring and alerting (e.g., Datadog, PagerDuty).|

---

## 10. Technology Justification

### 10.1 Why PostgreSQL?

|Capability<br><br>+<br><br>+<br><br>+|Benefit<br><br>+|
|---|---|
|**Set-Based Operations**<br><br>+|`SELECT DISTINCT` deduplicates millions of rows in seconds using hash aggregation.|
|**JOIN Optimization**<br><br>+|Hash joins and merge joins efficiently resolve foreign keys across large tables.|
|**Disk-Aware Engine**<br><br>+|PostgreSQL transparently spills to disk for operations exceeding `work_mem`, preventing OOM.|
|**ACID Compliance**<br><br>+|Transactions ensure the finalization phase is atomic; partial failures do not corrupt data.|
|**Mature Ecosystem**<br><br>+|Excellent tooling (pgAdmin, psql), monitoring, and community support.|

### 10.2 Why Python?

|Capability<br><br>+<br><br>+<br><br>+|Benefit<br><br>+|
|---|---|
|**File I/O (Pandas)**<br><br>+|`pd.read_csv(chunksize=...)` provides native chunked reading with minimal code.|
|**Text Parsing (Regex)**<br><br>+|Complex AGE code parsing (`Y15T24` → label) is trivial with `re` module.|
|**Generator Support**<br><br>+|First-class `yield` keyword enables elegant streaming patterns.|
|**SQLAlchemy Integration**<br><br>+|Seamless DataFrame-to-database loading via `to_sql()`.|
|**Ecosystem**<br><br>+|Rich libraries for logging, testing, profiling, and orchestration.|

### 10.3 Why Docker?

|Capability<br><br>+<br><br>+<br><br>+|Benefit<br><br>+|
|---|---|
|**Environment Isolation**<br><br>+|PostgreSQL runs in a container, avoiding conflicts with host system.|
|**Reproducibility**<br><br>+|`docker-compose.yml` ensures identical database setup across machines.|
|**Portability**<br><br>+|Pipeline can be deployed to any Docker-capable environment without modification.|

---

## 11. Data Flow Summary

### 11.1 The Streaming Loop

Extract yields chunk → Clean transforms chunk → Load inserts into staging → Loop repeats

This cycle continues until the file pointer reaches the end of the 3.6GB CSV file, requiring approximately **89 iterations** (8.9M rows ÷ 100k rows/chunk).

### 11.2 The Finalization Phase

Staging table (8.9M rows) → Batch SQL → Dimension tables (DISTINCT) → Fact table (JOINs)

This phase executes **once**, after the streaming loop completes, leveraging PostgreSQL's optimized query engine.

---

## 12. Appendix

### 12.1 Key Metrics

|Metric<br><br>+<br><br>+<br><br>+|Value<br><br>+|
|---|---|
|Source File Size<br><br>+|3.6 GB|
|Source Row Count<br><br>+|8.9 million|
|Source Column Count<br><br>+|41|
|Chunk Size<br><br>+|100,000 rows|
|Approximate Iterations<br><br>+|89|
|Peak Python Memory<br><br>+|~200-400 MB|
|Columns After Pruning<br><br>+|14|

### 12.2 Glossary

|Term<br><br>+<br><br>+<br><br>+|Definition<br><br>+|
|---|---|
|**Chunk**<br><br>+|A subset of rows (100,000) read from the source file in a single iteration.|
|**Generator**<br><br>+|A Python function using `yield` that produces values lazily, one at a time.|
|**Staging Table**<br><br>+|A temporary, denormalized table used to buffer data before final transformation.|
|**Star Schema**<br><br>+|A data warehouse schema with a central fact table surrounded by dimension tables.|
|**Surrogate Key**<br><br>+|An auto-generated integer primary key (e.g., `country_id`) used in place of natural keys.|
|**OOM Killer**<br><br>+|A Linux kernel process that terminates memory-hungry processes to prevent system crashes.|

---

**Document End**