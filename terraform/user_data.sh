#!/bin/bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io docker-compose-v2
usermod -aG docker ubuntu
systemctl enable --now docker
install -d -m 0755 /opt/wdi

cat >/etc/systemd/system/wdi-compose.service <<'UNIT'
[Unit]
Description=WDI PostgreSQL and Apache Superset containers
Wants=docker.service
After=docker.service network-online.target
ConditionPathExists=/opt/wdi/docker-compose.yml

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/wdi
ExecStart=/usr/bin/docker compose --env-file /opt/wdi/.env.compose up -d
ExecStop=/usr/bin/docker compose --env-file /opt/wdi/.env.compose stop
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable wdi-compose.service
