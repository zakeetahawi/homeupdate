#!/bin/bash
# Script to start all production services

PROJECT_DIR="/home/zakee/homeupdate"
cd "$PROJECT_DIR" || exit 1

# Start the main production script
exec ./لينكس/run-production.sh
