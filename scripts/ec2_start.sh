#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/aws_common.sh"
require_command aws

INSTANCE_ID="$(require_instance_id)"
REGION="$(aws_region)"
aws --region "$REGION" ec2 start-instances --instance-ids "$INSTANCE_ID" >/dev/null
aws --region "$REGION" ec2 wait instance-running --instance-ids "$INSTANCE_ID"
"$SCRIPT_DIR/instance_info.sh"
