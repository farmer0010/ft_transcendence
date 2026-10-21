#!/bin/sh
# Disaster-recovery rehearsal: backup -> wipe the DB -> restore -> verify row counts match.
# Requires the stack to already be running (`make up`).
set -eu

cd "$(dirname "$0")/.."
set -a
. ./.env
set +a

count_cabinets() {
    docker compose exec -T mariadb mariadb -u"$DB_USER" -p"$DB_PASSWORD" -N -e \
        "SELECT COUNT(*) FROM cabi.cabinet;" 2>/dev/null || echo "ERROR"
}

echo "== DR test: step 1/5 - recording current cabinet count =="
BEFORE=$(count_cabinets)
echo "cabinet count before: $BEFORE"
if [ "$BEFORE" = "ERROR" ] || [ "$BEFORE" = "0" ]; then
    echo "Refusing to run: expected a seeded, non-empty 'cabinet' table before starting (run 'make seed' first)." >&2
    exit 1
fi

echo "== DR test: step 2/5 - taking a fresh backup =="
docker compose exec -T backup /scripts/backup.sh

echo "== DR test: step 3/5 - wiping the database =="
docker compose exec -T mariadb mariadb -u"$DB_USER" -p"$DB_PASSWORD" -e \
    "DROP DATABASE IF EXISTS cabi; CREATE DATABASE cabi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
MID=$(count_cabinets)
echo "cabinet count after wipe (expected ERROR, table should not exist): $MID"

echo "== DR test: step 4/5 - restoring from the latest backup =="
docker compose exec -T backup /scripts/restore.sh mariadb

echo "== DR test: step 5/5 - verifying restored data =="
AFTER=$(count_cabinets)
echo "cabinet count after restore: $AFTER"

if [ "$BEFORE" = "$AFTER" ]; then
    echo "PASS: cabinet count matches before ($BEFORE) and after restore ($AFTER)"
    exit 0
else
    echo "FAIL: cabinet count mismatch, before=$BEFORE after=$AFTER" >&2
    exit 1
fi
