#!/bin/bash
# Restore a gzipped SQL backup into the project's Postgres DB
# Usage: db-restore.sh [/path/to/backup.sql.gz]

set -euo pipefail

PROJECT_DIR="/home/zakee/homeupdate"
DEFAULT_TEMP_DIR="$PROJECT_DIR/temp"

print() { echo -e "[db-restore] $*"; }
err() { echo -e "[db-restore][ERROR] $*" >&2; }

# Determine backup file: arg or latest in temp
if [ $# -ge 1 ]; then
  BACKUP_FILE="$1"
else
  BACKUP_FILE=$(ls -1t "$DEFAULT_TEMP_DIR"/backup-*.sql.gz 2>/dev/null | head -n1 || true)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
  err "لم يتم العثور على ملف النسخة الاحتياطية. مرر مسار الملف كوسيط أو ضع ملف backup-*.sql.gz داخل $DEFAULT_TEMP_DIR"
  exit 2
fi

print "استخدام ملف النسخة: $BACKUP_FILE"

# Try to export DB settings from Django settings if available
if [ -f "$PROJECT_DIR/crm/settings.py" ]; then
  eval $(python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crm.settings')
import django
django.setup()
from django.conf import settings
print(f"export DB_NAME='{settings.DATABASES['default'].get('NAME','')}'")
print(f"export DB_USER='{settings.DATABASES['default'].get('USER','')}'")
print(f"export DB_HOST='{settings.DATABASES['default'].get('HOST','')}'")
print(f"export DB_PORT='{settings.DATABASES['default'].get('PORT','')}'")
print(f"export DB_PASSWORD='{settings.DATABASES['default'].get('PASSWORD','')}'")
PY
  ) || true
fi

# Fallback defaults (match your settings.py defaults)
: ${DB_NAME:='crm_system'}
: ${DB_USER:='postgres'}
: ${DB_HOST:='localhost'}
: ${DB_PORT:='5432'}
: ${DB_PASSWORD:='5525'}

export PGPASSWORD="$DB_PASSWORD"

print "Target DB: $DB_NAME on $DB_HOST:$DB_PORT as $DB_USER"

# Check if DB exists
if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt 2>/dev/null | cut -d \| -f 1 | sed -e 's/^[ \t]*//' | grep -qx "$DB_NAME"; then
  print "قاعدة البيانات موجودة: $DB_NAME"
else
  print "قاعدة البيانات غير موجودة، سيتم إنشاؤها: $DB_NAME"
  if command -v createdb >/dev/null 2>&1; then
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -O "$DB_USER" "$DB_NAME"
  else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
  fi
  print "تم إنشاء قاعدة البيانات: $DB_NAME"
fi

print "بدء الاستعادة (قد يستغرق وقتاً)..."
gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
print "تمت الاستعادة بنجاح: $BACKUP_FILE -> $DB_NAME"

print "قائمة جداول public (أعلى نتيجة):"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt public.*" || true
