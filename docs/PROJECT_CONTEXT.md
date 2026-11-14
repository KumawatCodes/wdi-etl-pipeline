# WDI ETL Project Context

This document is a self-contained handoff for a person or AI assistant that needs to understand the project before changing or operating it. It describes the repository as inspected on 2026-10-19. Source code and the current Compose/Terraform files are the implementation authority; older design notes may describe earlier versions.

## Purpose

This project takes a World Bank World Development Indicators (WDI) SDMX CSV export, filters it to a selected set of indicators and years, reshapes the observations into a dimensional PostgreSQL warehouse, and serves that warehouse to Apache Superset. Superset is the browser-based analysis tool. The owner creates database connections, datasets, charts, filters, and dashboards manually in the Superset UI. No deployment script is intended to generate dashboard content.

There are two deployment contexts:

- **Local development:** the ETL runs from Python on the host and writes to PostgreSQL in Docker. Superset also runs in Docker.
- **AWS hosting:** Terraform provisions one EC2 host. Docker Compose runs PostgreSQL and Superset on that host. The data warehouse and Superset metadata use separate databases inside the same PostgreSQL server. The dashboard is accessed through an SSH tunnel.

## Architecture at a glance

```text
World Bank WDI CSV (data/raw/WB_WDI.csv)
        │
        ▼
Python ETL: Polars scan/filter → rename/cast → dimension and fact loads
        │
        ▼
PostgreSQL (wdi_db)
  ├── dim_country
  ├── dim_indicator
  ├── dim_date
  ├── dim_sex
  ├── dim_age
  ├── dim_urbanisation
  └── fact_wdi_data ── foreign keys to the six dimensions
        │ read-only Superset reader account
        ▼
Apache Superset (browser UI)
        │
        └── stores users, connections, charts and dashboards in superset_metadata

AWS: Browser → SSH local port forward → EC2 loopback:8088 → Superset
                           EC2 loopback:5432 → PostgreSQL
```

On AWS, PostgreSQL and the Superset web port are bound to `127.0.0.1`; the security group permits SSH from the configured administrator CIDR. There is no RDS, Kubernetes, load balancer, or publicly accessible database port. The EC2 root EBS volume is encrypted gp3 storage; Docker's named PostgreSQL volume resides on that persistent filesystem. EC2 stop/start retains EBS data, while the public IPv4 address can change.

## ETL behavior and warehouse model

`run_pipeline.py` is the entry point. It loads `.env`, takes the CSV path `data/raw/WB_WDI.csv`, constructs a PostgreSQL SQLAlchemy URL from `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`, and runs extract → transform → load.

1. `scripts/extract.py` uses Polars lazy CSV scanning. It selects 14 columns: country code/name, indicator code/name, unit, year, sex code/label, age code/label, urbanisation code/label, observation value, and observation status. It filters to 20 hard-coded WDI indicator codes and `TIME_PERIOD <= 2023`, then drops null observation values.
2. `scripts/transform.py` renames those source fields into lower-case warehouse names, casts year to `Int32` and value to `Float64`, and collects the lazy frame into memory.
3. `scripts/load.py` creates six unique dimension frames, appends dimensions, looks up their surrogate IDs from PostgreSQL, joins those IDs to the observation frame, and appends the resulting rows to `fact_wdi_data`.

The fact grain is one observation per country, indicator, year, sex, age, and urbanisation combination. Its value is `obs_value`; `obs_status` is retained. The SQL schema declares a unique constraint on this six-key grain, foreign keys to all six dimensions, and an index on country/indicator/date. Dimensions contain natural code/label information and generated integer surrogate keys.

**ETL repeat-run caution:** the loader uses `if_table_exists="append"`; it is not an upsert or a refresh process. The SQL uniqueness constraints can make a repeated load fail on already loaded dimension/fact keys. Do not rerun the ETL against a populated warehouse expecting it to update or deduplicate data. Make a backup first and design an explicit incremental or rebuild strategy before changing this behavior. `sql/schema.sql` begins by dropping warehouse tables and is destructive; it is not a routine initialization command. `sql/schema_safe.sql` creates missing tables without dropping existing objects.

The source dataset is large (the tracked documentation describes a 3.6 GB export), and the ETL collects transformed data into memory before loading. Ensure adequate local/EC2 memory and disk before running it. The current deployed warehouse was previously verified at 212,980 rows in `fact_wdi_data`; verify against current database state before relying on that historical count.

## PostgreSQL databases and Superset

The PostgreSQL server hosts two logically separate databases:

- `wdi_db`: warehouse tables. Superset should query this database with the provisioned `superset_reader` account, which is intended to be read-only.
- `superset_metadata`: Superset's own application database. It stores authentication and UI configuration, including database connections, datasets, charts, and dashboards created through the UI.

`docker/init.sql` creates the metadata database/reader setup when a **fresh** PostgreSQL data directory is initialized. Docker's PostgreSQL initialization scripts do not rerun on an already initialized named volume. `superset/superset_config.py` configures SQLAlchemy to use the metadata database. `superset-image/Dockerfile` builds the pinned Superset 6.0.0 image and installs the PostgreSQL psycopg2 driver; the compose tag is `wdi-superset:6.0.0-pgdriver1`.

`superset-bootstrap` is a Compose profile for metadata migrations (`superset db upgrade`), Superset initialization, and creating the configured administrator only if that username does not already exist. A successful `/health` response proves the process responds; it does not guarantee every UI page or metadata query succeeds.

## Repository map

| Path | Responsibility |
|---|---|
| `run_pipeline.py` | ETL orchestration and local database URL construction |
| `scripts/extract.py`, `transform.py`, `load.py` | CSV filtering, normalization, and dimensional warehouse load |
| `core/logging.py` | Shared logging setup |
| `sql/schema.sql` | Destructive schema recreation script; review before any use |
| `sql/schema_safe.sql` | Non-destructive create-if-missing warehouse schema |
| `docker-compose.yml` | Local/AWS PostgreSQL, Superset, bootstrap services, volumes and health checks |
| `docker/init.sql` | First-boot PostgreSQL setup, including metadata database/reader |
| `superset-image/Dockerfile` | Pinned Superset image plus PostgreSQL driver |
| `superset/superset_config.py` | Superset metadata connection and application configuration |
| `terraform/*.tf`, `terraform/user_data.sh` | EC2, SSH key pair, security group, encrypted root EBS, and host bootstrap |
| `scripts/backup_db.sh`, `restore_db.sh` | Custom-format dumps and guarded restores |
| `scripts/deploy.sh`, `bootstrap_superset.sh`, `verify_remote.sh` | Copy app/backups, safe first restore, Superset bootstrap, remote verification |
| `scripts/ec2_start.sh`, `ec2_stop.sh`, `instance_info.sh` | Compute lifecycle and current access instructions |
| `scripts/status.sh`, `logs.sh` | Service diagnostics |
| `scripts/provision_reader.sh`, `init_warehouse_schema.sh` | Warehouse reader/schema operations; inspect before use |
| `scripts/aws_common.sh`, `prepare_ssh_key.sh` | Shared AWS/SSH helpers and key setup |
| `docs/` | Architecture, decisions, design, data dictionary, and project handoff |
| `notebook/` | Exploratory notebooks; not the production ETL entry point |

## Common workflows

### Local stack

1. Create `.env.compose` from `.env.example` and set unique passwords and a persistent Superset secret key. Keep it out of version control.
2. Start PostgreSQL and Superset with `docker compose --env-file .env.compose up -d --build`.
3. Run the bootstrap profile when initializing or deliberately upgrading Superset metadata: `docker compose --profile bootstrap --env-file .env.compose run --rm superset-bootstrap`.
4. The local dashboard is published only on host loopback at `http://127.0.0.1:8088`.
5. Run the ETL using the repository's Python environment after confirming the warehouse target and whether the load is safe. The data file must exist at `data/raw/WB_WDI.csv`.

### Back up and deploy to AWS

1. Use `scripts/backup_db.sh` to create custom-format dumps for both databases in ignored `backups/`. It checks each archive with `pg_restore --list`, prints SHA-256 hashes, and reports the warehouse fact row count. Keep another copy off the EC2 host / outside the project machine before infrastructure changes.
2. Configure Terraform inputs in ignored `terraform/terraform.tfvars` and AWS credentials via the AWS CLI/profile. Do not put AWS credentials in `.env.compose`.
3. Review `terraform plan` before applying. `scripts/deploy.sh` is the application/data migration step; it requires both archive paths via `WDI_WAREHOUSE_BACKUP` and `SUPERSET_METADATA_BACKUP` and checks the EC2 host is running.
4. Deployment copies only necessary application files and the two selected archives, starts PostgreSQL, restores to empty databases, provisions the reader, bootstraps Superset, and enables `wdi-compose.service`. `scripts/restore_db.sh` refuses to restore into a database that already contains objects. Do not bypass that guard by dropping data.
5. Use `scripts/status.sh`, `scripts/logs.sh`, and `scripts/verify_remote.sh` for diagnostics. Use `scripts/instance_info.sh` for the current public IP, SSH command, and tunnel command. Open the printed local URL only after the SSH tunnel is running.
6. Use the UI to connect Superset to `wdi_db` through the read-only account and create analysis content manually.

### Stop and resume AWS compute

- `scripts/ec2_stop.sh` stops EC2 compute but leaves the encrypted EBS volume and its PostgreSQL data attached. EBS storage (and some other AWS resources) can still incur charges while the instance is stopped.
- `scripts/ec2_start.sh` starts the same instance; Docker/systemd is configured to bring the services back. The public IPv4 may change, so rerun `scripts/instance_info.sh` and reconnect the tunnel.
- Do not use Terraform destroy or disable termination safeguards casually. `prevent_destroy` and EC2 termination protection are deliberate data-preservation controls. A stopped instance is not the same as deleting the project, but it is also not a guarantee of zero AWS charges.

## Configuration and data safety

Secrets and local-only artifacts are ignored by `.gitignore`: `.env*`, `keys/`, `terraform/*.tfvars`, Terraform state/plans/provider cache, `backups/`, and dump files. Never add secrets, private keys, database dumps, or Terraform state to git. `.env.compose` is for application settings; AWS credentials belong in the AWS CLI credential chain/profile.

Preserve existing PostgreSQL volumes and databases. Never run `docker compose down -v`, use `DROP DATABASE`, or run the destructive `sql/schema.sql` without a deliberate, separately verified rebuild plan and external backups. Do not restore over a non-empty database. Back up both `wdi_db` and `superset_metadata`: preserving only the warehouse loses Superset's saved users and UI configuration; preserving only metadata loses the actual WDI data.

The AWS stack uses a default VPC/subnet selected by Terraform, one EC2 instance, a security group restricted to `my_ip_cidr`, and encrypted persistent root EBS. The EC2 type in configuration is `m7i-flex.large`; free-tier/student credits and instance eligibility are account-specific and must not be assumed. Stopping compute reduces compute charges but does not remove storage charges.

## Current operational notes

- The user has applied Terraform and deployed the host/data. Previously reported values were region `ap-south-1`, instance `i-0b545d3385a2fd53d`, and public IP `13.233.118.79`; the address may now have changed. Query AWS/scripts for current state instead of relying on these historical values.
- Both source archives previously passed `pg_restore --list`; the source warehouse count was 212,980 rows. Treat those as historical verification, not a live check.
- The remote Superset health endpoint returned HTTP 200 through the SSH tunnel. The browser UI then showed an internal server error, with a SQL query against the Superset metadata table `themes`. The available log excerpt omitted the database error detail, so the cause is not established. A metadata bootstrap/migration command was run afterward, but no complete follow-up verification was recorded. If it persists, inspect the latest full Superset logs around the first SQL error, check `docker compose ps -a`, and verify migrations against a backup of `superset_metadata` before making database changes.
- SSH key access and Docker socket permission problems occurred during setup and were addressed in deployment scripts by explicit identity selection and adding `ubuntu` to the Docker group. If a newly logged-in session still reports Docker permission denied, reconnect SSH so the updated group membership is applied.

## Documentation caveat

Some older material, especially `docs/ETL-Pipeline.md` and parts of `docs/DATA_DICTIONARY.md`, describes a different pipeline (including staging tables, chunked pandas processing, older row counts, or columns not used by current code). Current behavior is defined by `run_pipeline.py`, `scripts/extract.py`, `scripts/transform.py`, `scripts/load.py`, and the current SQL/Compose files. Update those older docs separately after confirming the intended future design; do not infer current implementation from them.
