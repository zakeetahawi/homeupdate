#!/usr/bin/env bash
set -euo pipefail

# setup-postgres-systemd.sh
# Creates a systemd drop-in override to add Restart=on-failure for the postgres service.
# Run this script with sudo. It will not continue without root.

OVERRIDE_DIR="/etc/systemd/system/postgresql.service.d"
OVERRIDE_FILE="$OVERRIDE_DIR/override.conf"

if [[ $(id -u) -ne 0 ]]; then
  cat <<'MSG'
This script must be run as root (sudo).
It will create a systemd drop-in override to ensure postgresql restarts on failure.

Run:
  sudo bash scripts/setup-postgres-systemd.sh

MSG
  exit 1
fi

mkdir -p "$OVERRIDE_DIR"
cat > "$OVERRIDE_FILE" <<'UNIT'
[Service]
Restart=on-failure
RestartSec=5
UNIT

systemctl daemon-reload
systemctl restart postgresql || true
systemctl status postgresql --no-pager

echo
echo "Override written to: $OVERRIDE_FILE"
echo "If you prefer to inspect before applying, open that file and then run: systemctl daemon-reload && systemctl restart postgresql"

exit 0
