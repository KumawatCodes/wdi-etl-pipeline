# Real-World Troubleshooting & Incident Resolution Log

This document records the technical incidents, unexpected failures, root-cause analyses, and verified resolutions encountered during the engineering and CI/CD lifecycle of the WDI ETL platform.

---

### Incident 1: Linux Kernel Shebang Failure on Paths with Spaces

* **Component:** Local Python Virtual Environment (`.venv/bin/pytest`)
* **Symptom:** Running `.venv/bin/pytest` immediately terminated with:
  ```text
  /home/zenitsu/Data: bad interpreter: No such file or directory
  ```
* **Root Cause:** The absolute project directory path contains spaces (`/home/zenitsu/Data & AI/...`). The Linux kernel does not split words in the initial `#!` shebang header, interpreting everything after the first whitespace as an invalid command argument.
* **Engineering Solution:** Replaced the static kernel shebang in `.venv/bin/pytest` with a bash script wrapper that dynamically calculates its directory and wraps execution safely:
  ```bash
  #!/usr/bin/env bash
  DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  exec "$DIR/python" -m pytest "$@"
  ```
* **Verification:** `pytest -v tests/` executed smoothly and passed 12/12 test cases.
* **Lesson Learned:** Shebang wrappers in virtual environments must be resilient to arbitrary workspace directory paths containing whitespace or special characters.

---

### Incident 2: Python 3.12+ Import Failure on Legacy `pathlib` Backport

* **Component:** Python Runtime & Dependency Resolution (`pyproject.toml`)
* **Symptom:** Invoking any test module resulted in a fatal import error:
  ```text
  ImportError: cannot import name 'Sequence' from 'collections' (/usr/lib/python3.12/collections/__init__.py)
  ```
* **Root Cause:** The project's dependencies included `pathlib>=1.0.1`. This is an obsolete third-party backport originally published for Python 2.7. Python 3.4+ includes `pathlib` natively in the standard library. In Python 3.10+, abstract base classes were removed from `collections` and moved to `collections.abc`, causing the obsolete backport package to crash on load.
* **Engineering Solution:**
  1. Removed `pathlib>=1.0.1` from `pyproject.toml`.
  2. Disabled the backport file in `.venv/lib/python3.12/site-packages/pathlib.py`.
  3. Re-ran dependency resolution using Python's native standard library module.
* **Verification:** `python3 -c "import pathlib; print(pathlib.__file__)"` confirmed resolution to Python's internal standard library; all 12 tests passed.
* **Lesson Learned:** Never specify third-party backports for modules that have been promoted into the standard library.

---

### Incident 3: Terraform CI Stage Failure on Clean SCM Checkout

* **Component:** Jenkins CI/CD Pipeline (Stage 5: Terraform Validation)
* **Symptom:** In Jenkins Build #3, the pipeline aborted at Stage 5 with:
  ```text
  Error: registry.terraform.io/hashicorp/aws: there is no package for
  registry.terraform.io/hashicorp/aws 5.100.0 cached in .terraform/providers
  ```
* **Root Cause:** In earlier builds, the pipeline copied files from a local volume mount containing an already-initialized `.terraform` cache. When switched to clean SCM checkouts directly from GitHub, `.terraform` was excluded (per `.gitignore` standards). Running `terraform validate` requires providers to be initialized first.
* **Engineering Solution:**
  1. Updated Stage 5 in [Jenkinsfile](file:///home/zenitsu/Data%20%26%20AI/projects/wdi-etl-pipeline/Jenkinsfile) to execute `terraform -chdir=terraform init -backend=false` prior to `terraform validate`.
  2. Configured a persistent Terraform plugin cache in `/var/jenkins_home/.terraform.d/plugin-cache` to eliminate repeated provider downloads across builds.
* **Verification:** Subsequent pipeline builds successfully verified HCL formatting and validated provider syntax in under 3 seconds.
* **Lesson Learned:** Clean CI environments must explicitly initialize provider plugins with `-backend=false` before executing validation.

---

### Incident 4: Jenkins SCM Polling Inactivity Due to Historic Build State

* **Component:** Jenkins SCM Polling Engine (`WorkflowJob.poll()`)
* **Symptom:** After configuring Poll SCM (`H/3 * * * *`), the polling log reported:
  ```text
  Started on Nov 17, 2026, 3:07:25 PM
  Done. Took 0 ms
  No changes
  ```
  Even after pushing new commits to GitHub, the poll took 0 ms and failed to detect upstream changes.
* **Root Cause:** Decompilation and inspection of `WorkflowJob.poll()` revealed that Jenkins evaluates polling by calling `getLastSuccessfulBuild().checkouts()`. Build #2 (the last successful build) used local volume copying and recorded zero checkouts (`checkouts: []`). Consequently, the poller looped over an empty checkout list and immediately returned `NO_CHANGES`.
* **Engineering Solution:**
  1. Triggered a build using Git SCM checkout that successfully completed (Build #5).
  2. Once Build #5 became `lastSuccessfulBuild`, its checkout list registered `hudson.plugins.git.GitSCM`.
  3. Subsequent polling cycles executed `git ls-remote`, detected new commit `fbdfb87`, and automatically triggered Build #6 with trigger cause `"Started by an SCM change"`.
* **Verification:** Confirmed in `scmPollLog`: `Changes found. Latest remote head revision: fbdfb87...`. Build #6 triggered automatically.
* **Lesson Learned:** In Jenkins Pipeline jobs, SCM polling requires at least one successful build with a registered Git SCM checkout to establish the polling baseline.

---

### Incident 5: REST API 403 Forbidden Errors (Jenkins CSRF Protection)

* **Component:** Jenkins REST API & Automation CLI
* **Symptom:** Programmatic `curl -X POST` requests to trigger builds returned:
  ```text
  HTTP ERROR 403 No valid crumb was included in the request
  ```
* **Root Cause:** Jenkins default security enforces Cross-Site Request Forgery (CSRF) protection via session-bound crumb tokens. Simple unauthenticated or stateless POST requests lack the required `Jenkins-Crumb` header and matching HTTP session cookie.
* **Engineering Solution:** Implemented two-step API requests using a curl cookie jar:
  ```bash
  CRUMB=$(curl -s -u "admin:admin123" -c /tmp/cookies.txt "http://localhost:8080/crumbIssuer/api/json" | jq -r .crumb)
  curl -s -u "admin:admin123" -b /tmp/cookies.txt -H "Jenkins-Crumb: $CRUMB" -X POST "http://localhost:8080/job/WDI-ETL-Pipeline/build"
  ```
* **Verification:** API build triggering succeeded consistently without 403 errors.
* **Lesson Learned:** Always maintain cookie session state when exchanging CSRF crumb tokens with Jenkins.
