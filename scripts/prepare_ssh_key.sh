#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
KEY_DIR="$PROJECT_ROOT/keys"
KEY_PATH="$KEY_DIR/wdi-superset-admin"

mkdir -p "$KEY_DIR"
if [[ -e "$KEY_PATH" || -e "$KEY_PATH.pub" ]]; then
  if [[ -f "$KEY_PATH" && -f "$KEY_PATH.pub" ]]; then
    echo "SSH key already exists: $KEY_PATH"
    exit 0
  fi
  echo "Incomplete key pair found at $KEY_PATH; inspect it before continuing." >&2
  exit 1
fi

ssh-keygen -q -t ed25519 -a 64 -N "" -C "wdi-superset-admin" -f "$KEY_PATH"
chmod 600 "$KEY_PATH"
chmod 644 "$KEY_PATH.pub"
echo "Created a local SSH key pair. Keep the private key private: $KEY_PATH"
