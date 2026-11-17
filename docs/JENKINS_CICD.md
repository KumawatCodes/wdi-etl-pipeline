# Jenkins CI/CD Automation Pipeline

## 1. Executive Summary & Architecture Overview

The WDI ETL and Analytics platform processes large-scale World Bank datasets and provisions cloud infrastructure on AWS. To ensure software quality, regression avoidance, configuration compliance, and infrastructure safety, a **Continuous Integration and Continuous Delivery (CI/CD)** pipeline is implemented via a declarative `Jenkinsfile`.

The CI/CD pipeline acts as an automated quality gate before any code or infrastructure changes reach the production environment.

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 JENKINS CI/CD WORKFLOW                                 │
├───────────────┬─────────────────┬─────────────────┬──────────────────┬─────────────────┤
│    STAGE 1    │     STAGE 2     │     STAGE 3     │     STAGE 4      │     STAGE 5     │
│   Checkout    │   Environment   │   Validation    │  Automated Tests │  Terraform HCL  │
├───────────────┼─────────────────┼─────────────────┼──────────────────┼─────────────────┤
│ Git commit    │ Verify Python   │ Bytecode syntax │ 12 Pytest tests  │ terraform fmt   │
│ & branch lock │ runtime & venv  │ & file presence │ & JUnit XML rep. │ & validate      │
└───────┬───────┴────────┬────────┴────────┬────────┴────────┬─────────┴────────┬────────┘
        │                │                 │                 │                  │
        ▼                ▼                 ▼                 ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTAINER & QUALITY GATE                                  │
├─────────────────────────────────────────────────┬──────────────────────────────────────┤
│                     STAGE 6                     │               STAGE 7                │
│                Docker Validation                │             Final Report             │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Validate Compose configuration & syntax         │ Aggregate build status & pass gate   │
│ Validate custom Superset Dockerfile (non-root)  │ Ready for Operator Review / Demo     │
└─────────────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 2. Pipeline Stages & Verification Responsibilities

| Stage | Name | Commands / Tools | Purpose & Quality Criteria |
| :---: | :--- | :--- | :--- |
| **1** | **Checkout** | `checkout scm`, `git rev-parse` | Clones target branch, records commit SHA, ensures clean working directory. |
| **2** | **Environment** | `python3 --version`, `.venv` verification | Ensures Python runtime compatibility and verifies isolated dependencies. |
| **3** | **Validation** | `python3 -m py_compile run_pipeline.py etl/*.py core/*.py` | Validates Python syntax, checks presence of mandatory schema/config files. |
| **4** | **Testing** | `pytest -v --junitxml=reports/test-results.xml tests/` | Runs 12 automated unit/integration tests for extraction, casting, and dimensional mapping. |
| **5** | **Terraform Validation** | `terraform fmt -check`, `terraform validate` | Enforces HCL formatting conventions and validates AWS provider configurations. |
| **6** | **Docker Validation** | `docker compose --env-file .env.example config --quiet` | Confirms Compose YAML schema, health checks, and non-root Dockerfile rules. |
| **7** | **Final Report** | Summary logger & quality gate | Emits structured build audit and marks job as SUCCESS. |

---

## 3. Automated Test Suite (Pytest)

The test suite located under `tests/` tests real ETL transformations without mocks or placeholders:

* **Extraction (`tests/test_extract.py`):**
  * `test_required_columns_list`: Verifies 14 essential SDMX columns are defined.
  * `test_required_indicators_list`: Confirms all 20 WDI indicator codes are present.
  * `test_drop_null_obs_values`: Tests that rows with null observations are filtered out.
  * `test_lazyframe_filtering_logic`: Tests end-to-end Polars LazyFrame filter rules for indicator whitelist and year $\le 2023$.
* **Transformation (`tests/test_transform.py`):**
  * `test_rename_column`: Validates natural-to-warehouse column mapping dictionary.
  * `test_cast_col`: Verifies year cast to `Int32` and observation value cast to `Float64`.
  * `test_transform_lf_end_to_end`: Validates schema width, height, and types of transformed DataFrame.
* **Loading & Schema Integrity (`tests/test_load.py`):**
  * `test_build_dim_country`: Tests unique sorted extraction of country dimension.
  * `test_build_dim_indicator`: Tests indicator dimension metadata extraction.
  * `test_build_dim_date`: Tests reporting year dimension extraction.
  * `test_build_demographic_dimensions`: Tests sex, age, and urbanisation dimension generation.
  * `test_fact_mapping_integrity`: Validates foreign key surrogate joins, ensuring zero null foreign keys exist in fact table.

---

## 4. Live Jenkins LTS Docker Service

A production-grade Jenkins LTS instance is deployed locally via Docker Compose (`jenkins/docker-compose.yml`) with persistent storage and pre-configured pipeline automation:

* **Web UI URL:** [http://localhost:8080](http://localhost:8080)
* **Pre-configured Username:** `admin`
* **Pre-configured Password:** `admin123`
* **Pipeline Job Name:** `WDI-ETL-Pipeline`
* **Container Name:** `wdi-jenkins`
* **Persistent Storage Volume:** `wdi-jenkins-ci_jenkins_home`
* **Installed Tooling in Container:** Python 3.13, Pytest 9.2, Polars 2.1, SQLAlchemy 2.0, Terraform 1.17, Docker CLI.

### Triggering a Build via Jenkins API:
```bash
# Obtain CSRF Crumb and trigger Build
CRUMB=$(curl -s -c /tmp/cookies.txt -u "admin:admin123" 'http://localhost:8080/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)')
curl -s -b /tmp/cookies.txt -u "admin:admin123" -H "$CRUMB" -X POST http://localhost:8080/job/WDI-ETL-Pipeline/build

# Check Build Status & Duration
curl -s -u "admin:admin123" http://localhost:8080/job/WDI-ETL-Pipeline/lastBuild/api/json | jq '{id: .id, result: .result, duration: .duration}'
```

---

## 5. Local CI Pipeline Script (Stand-Alone Simulation)

For quick offline verification and terminal-only presentation without opening the browser, the runner script simulates all 7 stages:

```bash
scripts/run_ci_pipeline.sh
```

**Expected Console Output:**
```text
==========================================================
          STARTING WDI ETL CI/CD PIPELINE RUN             
==========================================================

>>> [STAGE 1/7] Checkout & Workspace Verification
Repository: wdi-etl-pipeline
Active Branch: master (Commit: 867be70)
Status: PASSED

>>> [STAGE 2/7] Environment Setup
Using Python: Python 3.14.10
Virtual Environment: Verified
Status: PASSED

>>> [STAGE 3/7] Project Validation & Static Syntax Checks
Critical files verified. Syntax compiled cleanly.
Status: PASSED

>>> [STAGE 4/7] Automated Testing (Pytest)
collected 12 items
tests/test_extract.py ....                                               [ 33%]
tests/test_load.py .....                                                 [ 75%]
tests/test_transform.py ...                                              [100%]
12 passed in 0.40s
Status: PASSED

>>> [STAGE 5/7] Infrastructure as Code (Terraform) Validation
Success! The configuration is valid.
Status: PASSED

>>> [STAGE 6/7] Docker Compose & Image Validation
Docker configurations validated.
Status: PASSED

==========================================================
             WDI ETL CI/CD PIPELINE SUMMARY               
==========================================================
 [PASS] Stage 1: Checkout
 [PASS] Stage 2: Environment
 [PASS] Stage 3: Python Syntax & Config Validation
 [PASS] Stage 4: Pytest Suite (12 Unit Tests Passed)
 [PASS] Stage 5: Terraform HCL Formatter & Validator
 [PASS] Stage 6: Docker Compose & Image Validation
==========================================================
 BUILD STATUS: SUCCESS - Ready for Presentation
==========================================================
```

---

## 5. Deployment Safeguards & Production Boundary

To prevent accidental production data corruption, **automated continuous deployment (CD) is deliberately disabled**. In accordance with enterprise data engineering standards:
1. Database schema and data changes require verified custom-format dumps (`scripts/backup_db.sh`).
2. Remote deployment is guarded by `scripts/deploy.sh` and only applies to empty databases to prevent overwrites.
3. Terraform state changes are operator-reviewed before `apply`.
