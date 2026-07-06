# WDI Global Development ETL Pipeline

A production-style ETL pipeline that ingests the World Bank's World Development Indicators (WDI) dataset — 8.9M rows, 3.6GB, SDMX format — cleans it, transforms it into a star schema, and loads it into a PostgreSQL database for analysis.

**Status:** ✅ ETL pipeline complete. Full 3.6GB load validated.

## Business Problem

> An NGO wants to analyze the relationship between a country's GDP growth and life expectancy over the last 20 years to prioritize development funding.

## Dataset

- **Source:** World Bank Databank — World Development Indicators (SDMX export)
- **File:** `WB_WDI.csv` — 8,894,932 rows × 41 columns, 3.6GB
- **Format:** Long format (one row per observation)
- **Note:** Indicator codes use the prefix `WB_WDI_` with dots replaced by underscores — e.g. `NY.GDP.PCAP.KD` → `WB_WDI_NY_GDP_PCAP_KD`

## Architecture

```
WB_WDI.csv (3.6GB)
    │
    │  pandas read_csv(chunksize=100,000)
    ▼
extract.py ── drops 27 constant/plumbing columns (41 → 15 cols per chunk)
    │
    │  yields one chunk at a time (~100k rows)
    ▼
clean.py ── validates code/label pairs, decodes AGE codes, drops null OBS_VALUE
    │
    │  clean chunk appended to staging table
    ▼
load.py ── staging_wdi_raw (flat, no constraints, transient)
    │
    │  finalize_load(): pure SQL batch inserts into star schema
    ▼
PostgreSQL (Docker) ── dim_country, dim_indicator, dim_date,
                        dim_sex, dim_age, dim_urbanisation, fact_wdi_data
```

Full pipeline diagram: `docs/diagrams/pipeline-architecture.png` Star schema diagram: `docs/diagrams/star-schema.png`

## Tech Stack

|Category|Tool|
|---|---|
|Package management|`uv`|
|Language|Python 3.10+|
|Processing|pandas (chunked reads)|
|Database|PostgreSQL 16 via Docker|
|ORM / DB driver|SQLAlchemy + psycopg2|
|Testing|pytest|

## Project Structure

```
wdi-etl-pipeline/
├── README.md
├── docker-compose.yml        # Postgres container + auto schema init
├── pyproject.toml            # uv-managed dependencies
├── run_pipeline.py           # Orchestrator: extract → clean → load
├── docs/
│   ├── DATA_DICTIONARY.md
│   ├── DESIGN.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── diagrams/
│       ├── star-schema.png
│       └── pipeline-architecture.png
├── data/
│   ├── raw/                  # WB_WDI.csv goes here (gitignored, 3.6GB)
│   └── samples/              # sample_5000.csv — safe to commit, use for testing
├── sql/
│   └── schema.sql            # CREATE TABLE statements (auto-applied by Docker)
├── scripts/
│   ├── __init__.py
│   ├── extract.py
│   ├── clean.py
│   └── load.py
└── tests/
    └── test_data_quality.py
```

---

## Setup & Running the Pipeline

### Prerequisites

- Docker installed and running
- `uv` installed — if not: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Step 1 — Clone the repo

```bash
git clone https://github.com/your-username/wdi-etl-pipeline.git
cd wdi-etl-pipeline
```

### Step 2 — Install Python dependencies

```bash
uv sync
```

### Step 3 — Start the database

```bash
docker compose up -d
```

This starts a PostgreSQL 16 container named `wdi_postgres` on port `5432`. On first start, Docker automatically runs `sql/schema.sql` — all 6 tables (5 dimensions + fact) are created for you. Nothing manual needed.

Verify it started:

```bash
docker ps
# You should see: wdi_postgres   postgres:16   Up X seconds   0.0.0.0:5432->5432/tcp
```

### Step 4 — Add the data file

**Option A — Sample only (quick test, no download needed):** The repo includes `data/samples/sample_5000.csv` — 5,000 rows, enough to verify the full pipeline runs correctly without waiting for a large load.

**Option B — Full dataset (real run):**

1. Go to [World Bank Databank](https://databank.worldbank.org/source/world-development-indicators)
2. Download the SDMX export — file will be named `WB_WDI.csv` (~3.6GB)
3. Place it at `data/raw/WB_WDI.csv` (this path is gitignored — the file will never be accidentally committed)

### Step 5 — Run the pipeline

**On the sample (recommended first run):**

```bash
uv run python run_pipeline.py data/samples/sample_5000.csv
```

Expected output:

```
[run_pipeline] Connected to wdi_db at localhost:5432
[run_pipeline] Starting pipeline on data/samples/sample_5000.csv
  chunk 1: 5000 rows read (running total: 5000)
[run_pipeline] Chunk 1: 5000 raw → 4987 cleaned → 4987 loaded
[run_pipeline] Done. 4987 rows loaded in 2.3s
```

**On the full file:**

```bash
uv run python run_pipeline.py data/raw/WB_WDI.csv
```

Expected time: under 10 minutes on a standard laptop.

### Step 6 — Validate the load

Connect to the database with any Postgres client (DBeaver, psql, TablePlus):

```
Host:     localhost
Port:     5432
Database: wdi_db
User:     wdi_user
Password: wdi_pass
```

Run the validation query:

```sql
SELECT c.country_name, i.indicator_name, d.year, f.obs_value
FROM fact_wdi_data f
JOIN dim_country c      ON f.country_id   = c.country_id
JOIN dim_indicator i    ON f.indicator_id = i.indicator_id
JOIN dim_date d         ON f.date_id      = d.date_id
JOIN dim_sex s          ON f.sex_id       = s.sex_id
JOIN dim_age a          ON f.age_id       = a.age_id
JOIN dim_urbanisation u ON f.urban_id     = u.urban_id
WHERE c.country_code  = 'IND'
  AND i.indicator_code = 'WB_WDI_NY_GDP_PCAP_KD'
  AND d.year           = 2020
  AND s.sex_code       = '_T'
  AND a.age_code       = '_T'
  AND u.urban_code     = '_T';
```

Expected result: **one row**, `India | GDP per capita (constant 2015 US$) | 2020 | 1806.50`

---

## Resetting the Database

If you need a clean slate (re-run schema, reload data):

```bash
docker compose down -v       # removes container AND the data volume
docker compose up -d         # recreates container, re-applies schema.sql automatically
uv run python run_pipeline.py data/samples/sample_5000.csv
```

**Warning:** `docker compose down -v` permanently deletes all loaded data. Only do this when you actually want to start fresh.

---

## Running Tests

```bash
uv run pytest tests/
```

---

See `task_list.md` for the full phase-by-phase task breakdown.