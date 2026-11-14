# WDI AWS deployment architecture

## Services

```text
Browser on administrator laptop
  └── SSH local forward: 127.0.0.1:8088 → EC2 127.0.0.1:8088
       └── EC2 security group: TCP/22 from administrator CIDR only
            └── Ubuntu 24.04 LTS, ap-south-1
                 ├── Superset 6.0.0 Docker container
                 └── PostgreSQL 17.6 Docker container
                      ├── wdi_db
                      ├── superset_metadata
                      └── superset_reader (read-only WDI login)
```

Terraform provisions one `m7i-flex.large` EC2 host, a security group, an EC2 SSH key pair, and an encrypted 80 GiB gp3 root volume. PostgreSQL and Superset bind to EC2 loopback and are reached only over the SSH tunnel. No RDS, load balancer, Kubernetes, or public database port is used.

The PostgreSQL Docker volume is stored on the EBS-backed filesystem. Stopping and starting the EC2 instance preserves that volume. Docker restart policies and `wdi-compose.service` bring services back after reboot. The Terraform resource has termination protection and `prevent_destroy` enabled.

## Data migration

The local warehouse is exported using `pg_dump` custom format. Both `wdi_db` and `superset_metadata` are backed up. The deploy process validates archive readability and restores only into empty target databases; it does not drop or replace existing database objects. The remote archive is retained under the ignored `backups/` directory until an operator removes it deliberately.

Superset metadata holds users, database connections, and any UI objects created by the operator. Deployment does not create datasets, charts, filters, or dashboards. The operator creates them manually in Superset.

## Day-to-day operation

- `scripts/ec2_start.sh` starts the host and prints its current address.
- `scripts/instance_info.sh` prints the current SSH and tunnel commands.
- `scripts/status.sh` checks EC2, systemd, and Compose health.
- `scripts/logs.sh` follows a container log.
- `scripts/ec2_stop.sh` stops compute while retaining EBS data.
- `scripts/backup_db.sh` writes verified custom-format dumps for both databases.

The assigned public IPv4 changes after a stop/start. Scripts query EC2 for the current address. The AWS account's free usage or credits, quotas, and remaining balance must be checked independently before provisioning.
