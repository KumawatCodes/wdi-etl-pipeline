# WDI ETL + Superset Operations Runbook

Use these commands from the repository root: `/home/zenitsu/Data & AI/projects/wdi-etl-pipeline`. AWS account eligibility/credits and the current EC2 public IP are live values; scripts query AWS for the IP. Do not share `.env.compose`, private keys, database dumps, or Terraform state.

## 1. Daily workflow: start, use, stop

1. Start EC2, wait for it to be running, and open the SSH tunnel in the foreground:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/ec2_start.sh && IP="$(aws --region ap-south-1 ec2 describe-instances --instance-ids "$(terraform -chdir=terraform output -raw instance_id)" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)" && ssh -i "$PWD/keys/wdi-superset-admin" -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -N -L 8088:127.0.0.1:8088 "ubuntu@$IP"
   ```

   Keep this terminal open. If it reports SSH timeout, follow section 7.1.

2. Open **http://127.0.0.1:8088** in your browser. Sign in using your existing Superset account. A stop/start changes the EC2 public IP, but the command above fetches the new address.

3. When finished, close the tunnel with `Ctrl+C`. Then stop compute:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/ec2_stop.sh
   ```

   This stops EC2; it does not delete PostgreSQL data or Superset metadata. EBS storage remains billable.

## 2. Dashboard and connection persistence

1. Superset stores users, database connections, datasets, saved charts, and dashboards in PostgreSQL database `superset_metadata`. The WDI data is in the separate `wdi_db` database.
2. Both databases are in the same PostgreSQL container and named Docker volume `wdi_pgdata`, on the EC2 encrypted EBS root volume.
3. You do **not** reconnect after an EC2 stop/start or a normal container restart. Connections and dashboard objects persist in `superset_metadata`.
4. `docker compose stop` followed by `up -d`, `docker compose down` followed by `up -d`, EC2 reboot, and EC2 stop/start preserve the named volume. **Never use `docker compose down -v`.**
5. Dashboard work can be lost if the named volume/database is deleted or corrupted, the EBS volume is deleted, the instance is terminated and its disk is later discarded, Superset is pointed at a new empty metadata database, or a restore overwrites metadata. Keep an external metadata backup.
6. Back up both databases with `scripts/backup_db.sh` (section 5). If storage forces a choice, prioritize `superset_metadata` to preserve manually created dashboard work; the WDI data may be reloaded only if the original CSV and a safe ETL/rebuild process are available. Ideally retain both: they are small relative to the WDI source file.

## 3. First-time setup on a fresh EC2

This is a migration sequence, not a reset procedure. The deployment script requires verified custom-format archives and restores only to empty databases.

1. From the repository root, verify the configuration and local prerequisites:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   test -r .env.compose && test -r keys/wdi-superset-admin && test -r keys/wdi-superset-admin.pub
   terraform -chdir=terraform output -raw instance_id
   ```

   `.env.compose` must contain the configured database passwords, Superset secret key, and admin settings. Never print or commit it. AWS CLI credentials must be configured separately.

2. Before provisioning a genuinely fresh host, review Terraform:

   ```bash
   terraform -chdir=terraform plan -out=tfplan
   terraform -chdir=terraform show tfplan
   ```

   Confirm region `ap-south-1`, type `m7i-flex.large`, 80 GiB encrypted gp3, and the intended SSH CIDR. Terraform has `prevent_destroy` and EC2 termination protection. Apply only a reviewed plan:

   ```bash
   terraform -chdir=terraform apply tfplan
   ```

3. Back up the source databases and keep a second copy away from this machine:

   ```bash
   scripts/backup_db.sh
   ```

   Existing verified archives in this repository are `backups/wdi_db-20261018T172446Z.dump` and `backups/superset_metadata-20261018T172446Z.dump`. They are historical snapshots; make fresh backups if the local databases have changed.

4. Start EC2, install the deployment files, restore both databases, provision the read-only account, run Superset metadata migrations, and enable automatic service startup:

   ```bash
   scripts/ec2_start.sh
   WDI_WAREHOUSE_BACKUP=backups/wdi_db-20261018T172446Z.dump SUPERSET_METADATA_BACKUP=backups/superset_metadata-20261018T172446Z.dump scripts/deploy.sh
   ```

   `scripts/deploy.sh` copies files to `/opt/wdi`, starts PostgreSQL, validates/restores archives only into empty databases, runs `provision_reader.sh` and `bootstrap_superset.sh`, then enables `wdi-compose.service`. Do not rerun this against populated databases; its restore guard should stop it.

5. Confirm services and database access:

   ```bash
   scripts/status.sh
   scripts/verify_remote.sh
   ```

6. Start the tunnel using the command in section 1 and browse to **http://127.0.0.1:8088**. If this is a restored metadata database, sign in with the existing account from the backup. Bootstrap will not reset credentials for an existing administrator.

7. In Superset, add the WDI connection once: host `postgres`, port `5432`, database `wdi_db`, username `superset_reader`, password from `SUPERSET_READER_PASSWORD` in `.env.compose`. Use separate fields where available. If entering a URI, URL-encode reserved characters in the password. Test, save, then create datasets/charts/dashboards manually.

8. To initialize an empty WDI database instead of restoring a warehouse archive, after deploy files and PostgreSQL exist, run on EC2:

   ```bash
   cd /opt/wdi && ./scripts/init_warehouse_schema.sh
   ```

   The standard `deploy.sh` intentionally requires a WDI archive and is not the empty-database flow.

## 4. ETL pipeline

1. The CSV must be at `data/raw/WB_WDI.csv` relative to the repository root. The current ETL entry point is `run_pipeline.py`; it uses Polars to filter configured indicators and years through 2023, transform rows, and load the star schema.
2. Ensure local PostgreSQL is running and `.env` points to the intended target. Defaults in `run_pipeline.py` are `localhost:5432`, database `wdi_db`, user `wdi_user`; set `DB_PASSWORD` in `.env`. Start local services if needed with:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   docker compose --env-file .env.compose up -d postgres
   uv run python run_pipeline.py
   ```

3. To load into EC2, first start EC2 and create a **second SSH tunnel** for PostgreSQL in another terminal:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   IP="$(aws --region ap-south-1 ec2 describe-instances --instance-ids "$(terraform -chdir=terraform output -raw instance_id)" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)"
   ssh -i "$PWD/keys/wdi-superset-admin" -o IdentitiesOnly=yes -N -L 5432:127.0.0.1:5432 "ubuntu@$IP"
   ```

   In the ETL terminal, set `DB_HOST=127.0.0.1`, `DB_PORT=5432`, and `DB_PASSWORD` to the warehouse owner password, then run `uv run python run_pipeline.py`. Keep the tunnel open until ETL finishes. Do not run the full ETL on EC2 as a Compose service; it is not configured that way.

4. The repository has no measured run duration. It filters a large CSV, collects the filtered frame in memory, then loads dimensions and facts; runtime depends on the file, machine, and database. Do not promise a fixed duration. Check logs for “Pipeline completed successfully”.
5. Verify in PostgreSQL:

   ```sql
   SELECT COUNT(*) AS fact_rows FROM fact_wdi_data;
   SELECT COUNT(*) AS countries FROM dim_country;
   SELECT COUNT(*) AS indicators FROM dim_indicator;
   SELECT COUNT(*) AS years FROM dim_date;
   SELECT COUNT(*) AS orphan_facts
   FROM fact_wdi_data f
   LEFT JOIN dim_country c USING (country_id)
   LEFT JOIN dim_indicator i USING (indicator_id)
   LEFT JOIN dim_date d USING (date_id)
   WHERE c.country_id IS NULL OR i.indicator_id IS NULL OR d.date_id IS NULL;
   ```

   The historical migrated fact count was 212,980; compare with a fresh source backup/expected count, not as a guaranteed current value.

6. **A safe repeat load is not implemented.** The loader appends dimensions and facts and schema uniqueness constraints can make a second run fail; it is not an upsert, deduplicator, or transactional full refresh. Do not rerun against a populated warehouse. Back up first, then implement and validate an explicit staging/upsert or replace-from-verified-backup process before reloading. `sql/schema.sql` drops tables and is destructive; do not use it as a rerun shortcut.

## 5. Backup and restore

1. Create verified custom-format dumps of both databases:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/backup_db.sh
   ```

   Outputs go to ignored `backups/`, are checked with `pg_restore --list`, and get SHA-256 hashes. Copy them to a separate disk/location; local ignored files are not disaster recovery.

2. Restore a dump only into a deliberately empty database. On the host where the Compose stack is installed:

   ```bash
   cd /opt/wdi
   ./scripts/restore_db.sh /opt/wdi/backups/wdi_db.dump wdi_db
   ./scripts/restore_db.sh /opt/wdi/backups/superset_metadata.dump superset_metadata
   ```

   The script refuses non-empty targets and never drops existing objects. During initial migration, `deploy.sh` transfers the selected local archives and invokes this guard. For existing data, first back it up and use a separate recovery plan; do not work around the guard by dropping tables/databases.

## 6. Cost management and persistence

1. Resources in Terraform: one `m7i-flex.large` EC2 in Mumbai, one SSH-only security group, one EC2 key pair, and an encrypted 80 GiB gp3 root EBS volume (Docker data is on it). No RDS, NAT gateway, load balancer, or Elastic IP is configured.
2. README list-price estimate (not a quote): about **$0.10075 per running EC2 hour + $0.005 per public IPv4 hour + $0.0912 per GiB-month for 80 GiB gp3**, or roughly **$84.50/month** if running 730 hours. Stopped all month, EBS alone is roughly **$7.30/month**, plus any snapshots, data transfer, taxes, or retained resources. Student credits/free-tier eligibility vary by account; check Billing and current AWS pricing before use. AWS bills public IPv4 at $0.005/hour; gp3 storage is billed while provisioned. [AWS VPC pricing](https://aws.amazon.com/vpc/pricing/), [AWS EBS pricing](https://aws.amazon.com/ebs/pricing/).
3. Stop compute:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/ec2_stop.sh
   ```

4. Start compute:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/ec2_start.sh
   scripts/instance_info.sh
   ```

5. Stopping preserves the EBS root volume, Docker volume, both databases, and dashboards; it stops compute billing but EBS continues billing and the public IPv4 is released/changes. Termination/deleting the EBS volume can destroy data; `delete_on_termination=false`, termination protection, and Terraform `prevent_destroy` are safety controls, not a backup. Keep external dumps.

## 7. Troubleshooting

1. **SSH connection timeout:** EC2 may be stopped, or the security group may not allow your current public IP. Run `scripts/ec2_start.sh`, update `my_ip_cidr` as in section 8, apply the reviewed plan, then run `scripts/instance_info.sh`. Confirm `keys/wdi-superset-admin` is the private key and use `-o IdentitiesOnly=yes`.
2. **Superset internal server error:**

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   scripts/status.sh
   scripts/logs.sh superset
   ```

   Look for the first actual PostgreSQL error before the SQL query failure. Back up `superset_metadata` before metadata changes. If migration is incomplete, run on EC2:

   ```bash
   cd /opt/wdi && sudo docker compose --profile bootstrap --env-file .env.compose run --rm superset-bootstrap && sudo docker compose --env-file .env.compose restart superset
   ```

   Then refresh the page and inspect logs again. `/health` returning 200 does not prove every metadata table is valid.

3. **Containers not starting:**

   ```bash
   cd /opt/wdi
   sudo systemctl status wdi-compose.service --no-pager
   sudo docker compose --env-file .env.compose ps -a
   sudo docker compose --env-file .env.compose logs --tail=150 postgres superset
   sudo systemctl restart wdi-compose.service
   ```

   PostgreSQL must become healthy before Superset. Check disk with `df -h` if PostgreSQL fails to start. Do not delete volumes.

4. **Superset database connection lost or password rejected:** In Superset edit the saved database connection and confirm Host `postgres`, Port `5432`, DB `wdi_db`, user `superset_reader`. If password is out of sync, on EC2 run `cd /opt/wdi && sudo ./scripts/provision_reader.sh`, then re-enter the `SUPERSET_READER_PASSWORD` from `/opt/wdi/.env.compose`. For a URI, URL-encode reserved password characters; a raw `@` can be parsed as hostname text. Never send the password in chat/logs.
5. **Port 8088 inaccessible:** The tunnel must be running locally, the EC2 must be running, the local port 8088 must be unused, and the Superset container must be healthy. Check `scripts/status.sh`; restart the foreground tunnel from section 1. Do not open 8088 or 5432 to `0.0.0.0/0`; the security group is intentionally SSH-only.

## 8. Security group / public IP update (Jio CGNAT)

1. The current requested configuration is `my_ip_cidr = "152.58.0.0/16"` in the ignored `terraform/terraform.tfvars`. Confirm that value exists locally without printing other variables:

   ```bash
   cd "/home/zenitsu/Data & AI/projects/wdi-etl-pipeline"
   rg '^my_ip_cidr\s*=' terraform/terraform.tfvars
   ```

2. If it differs, edit only that variable in `terraform/terraform.tfvars` to the stated CIDR. A `/16` allows a very broad range of source addresses; use it only if necessary for CGNAT, and narrow it when practical. SSH remains the only ingress port.
3. Review and apply only the security group change:

   ```bash
   terraform -chdir=terraform plan -out=tfplan
   terraform -chdir=terraform show tfplan
   terraform -chdir=terraform apply tfplan
   ```

   Confirm the plan changes the SSH CIDR and does not replace/destroy EC2 or EBS. Then retry `scripts/instance_info.sh` and SSH. If the address changes often, update the CIDR and repeat this reviewed plan/apply sequence.

## 9. Key files and operational invariants

1. ETL source: `run_pipeline.py`, `scripts/extract.py`, `scripts/transform.py`, `scripts/load.py`.
2. Runtime: `docker-compose.yml`, `docker/init.sql`, `superset/superset_config.py`, `superset-image/Dockerfile`.
3. AWS: `terraform/main.tf`, `terraform/variables.tf`, `terraform/user_data.sh`.
4. Operations: `scripts/deploy.sh`, `backup_db.sh`, `restore_db.sh`, `bootstrap_superset.sh`, `verify_remote.sh`, `status.sh`, `logs.sh`, `instance_info.sh`, `ec2_start.sh`, `ec2_stop.sh`.
5. Never run `docker compose down -v`, destructive `sql/schema.sql`, `DROP DATABASE`, or Terraform destroy when retaining data/dashboard work. Never commit `.env.compose`, `keys/`, backups, or Terraform state.
6. `docs/ETL-Pipeline.md` and parts of `docs/DATA_DICTIONARY.md` describe a past pandas/chunked staging architecture. The current code uses Polars lazy scan followed by collecting the transformed frame; trust the source code and this runbook for current behavior.
