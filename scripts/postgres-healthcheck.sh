#!/usr/bin/env bash
set -euo pipefail

# postgres-healthcheck.sh
# Checks whether Postgres is accepting connections on localhost:5432 and logs to logs/postgres-monitor.log

LOGFILE="$(dirname "$0")/../logs/postgres-monitor.log"
mkdir -p "$(dirname "$LOGFILE")"

TIMESTAMP=$(date --iso-8601=seconds)

if command -v pg_isready >/dev/null 2>&1; then
	if pg_isready -q -h localhost -p 5432; then
		echo "$TIMESTAMP - OK - postgres accepting connections" >>"$LOGFILE"
		exit 0
	else
		echo "$TIMESTAMP - FAIL - postgres not accepting connections" >>"$LOGFILE"
		exit 2
	fi
else
	echo "$TIMESTAMP - ERROR - pg_isready not found in PATH" >>"$LOGFILE"
	exit 3
fi
