#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$PROJECT_ROOT/terraform"
SSH_KEY_PATH="${SSH_KEY_PATH:-$PROJECT_ROOT/keys/wdi-superset-admin}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_instance_id() {
  require_command terraform
  local id
  id="$(terraform -chdir="$TF_DIR" output -raw instance_id 2>/dev/null || true)"
  if [[ -z "$id" ]]; then
    echo "No instance_id output. Apply the reviewed Terraform configuration first." >&2
    exit 1
  fi
  printf '%s\n' "$id"
}

aws_region() {
  terraform -chdir="$TF_DIR" output -raw aws_region
}

live_instance() {
  local id region
  id="$(require_instance_id)"
  region="$(aws_region)"
  aws --region "$region" ec2 describe-instances \
    --instance-ids "$id" \
    --query 'Reservations[0].Instances[0].[State.Name,PublicIpAddress]' \
    --output text
}

ssh_to_instance() {
  local ip="$1"
  if [[ -z "$ip" || "$ip" == "None" ]]; then
    echo "Instance has no public IP yet. Check its state and try again." >&2
    return 1
  fi
  if [[ ! -r "$SSH_KEY_PATH" ]]; then
    echo "Private SSH key not found/readable: $SSH_KEY_PATH" >&2
    echo "Run scripts/prepare_ssh_key.sh or set SSH_KEY_PATH." >&2
    return 1
  fi
}
