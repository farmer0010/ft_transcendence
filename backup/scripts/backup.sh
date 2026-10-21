#!/bin/sh
set -eu

: "${DB_HOST:=mariadb}"
: "${DB_NAME:=cabi}"
: "${REDIS_HOST:=redis}"
: "${BACKUP_DIR:=/backups}"
: "${REDIS_DATA_DIR:=/redis_data}"
: "${BACKUP_RETENTION_COUNT:=7}"

TS=$(date +%Y%m%d_%H%M%S)
MARIADB_DIR="$BACKUP_DIR/mariadb"
REDIS_DIR="$BACKUP_DIR/redis"
mkdir -p "$MARIADB_DIR" "$REDIS_DIR"

echo "[backup] $TS: starting MariaDB dump of '$DB_NAME'"
mariadb-dump -h "$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" \
    --single-transaction --routines --triggers "$DB_NAME" \
    | gzip > "$MARIADB_DIR/cabi_${TS}.sql.gz.tmp"
mv "$MARIADB_DIR/cabi_${TS}.sql.gz.tmp" "$MARIADB_DIR/cabi_${TS}.sql.gz"
echo "[backup] $TS: MariaDB dump written to $MARIADB_DIR/cabi_${TS}.sql.gz"

echo "[backup] $TS: triggering Redis BGSAVE"
redis-cli -h "$REDIS_HOST" BGSAVE >/dev/null
# BGSAVE is async; poll until it finishes before copying the snapshot file.
i=0
while [ "$(redis-cli -h "$REDIS_HOST" INFO persistence | tr -d '\r' | grep '^rdb_bgsave_in_progress:' | cut -d: -f2)" = "1" ]; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
        echo "[backup] $TS: WARNING redis BGSAVE did not finish in time, skipping redis backup"
        exit 1
    fi
    sleep 1
done

if [ -f "$REDIS_DATA_DIR/dump.rdb" ]; then
    cp "$REDIS_DATA_DIR/dump.rdb" "$REDIS_DIR/dump_${TS}.rdb"
    echo "[backup] $TS: Redis snapshot written to $REDIS_DIR/dump_${TS}.rdb"
else
    echo "[backup] $TS: WARNING $REDIS_DATA_DIR/dump.rdb not found, skipping redis backup"
fi

# Retention: keep only the newest BACKUP_RETENTION_COUNT files per type.
for dir in "$MARIADB_DIR" "$REDIS_DIR"; do
    count=$(ls -1t "$dir" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$count" -gt "$BACKUP_RETENTION_COUNT" ]; then
        ls -1t "$dir" | tail -n +$((BACKUP_RETENTION_COUNT + 1)) | while IFS= read -r old; do
            echo "[backup] $TS: pruning old backup $dir/$old (retention=$BACKUP_RETENTION_COUNT)"
            rm -f "$dir/$old"
        done
    fi
done

date > "$BACKUP_DIR/.last_success"
echo "[backup] $TS: done"
