#!/bin/sh
set -eu

: "${DB_HOST:=mariadb}"
: "${DB_NAME:=cabi}"
: "${BACKUP_DIR:=/backups}"
: "${REDIS_DATA_DIR:=/redis_data}"

TARGET="${1:-mariadb}"
FILE="${2:-}"

restore_mariadb() {
    dir="$BACKUP_DIR/mariadb"
    if [ -z "$FILE" ]; then
        FILE=$(ls -1t "$dir" 2>/dev/null | head -n 1 || true)
    fi
    if [ -z "$FILE" ]; then
        echo "[restore] no mariadb backup found in $dir" >&2
        exit 1
    fi
    path="$dir/$FILE"
    if [ ! -f "$path" ]; then
        echo "[restore] backup file not found: $path" >&2
        exit 1
    fi
    echo "[restore] restoring MariaDB '$DB_NAME' from $path"
    mariadb -h "$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" -e \
        "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    gunzip -c "$path" | mariadb -h "$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"
    echo "[restore] MariaDB restore complete"
}

restore_redis() {
    dir="$BACKUP_DIR/redis"
    if [ -z "$FILE" ]; then
        FILE=$(ls -1t "$dir" 2>/dev/null | head -n 1 || true)
    fi
    if [ -z "$FILE" ]; then
        echo "[restore] no redis backup found in $dir" >&2
        exit 1
    fi
    path="$dir/$FILE"
    if [ ! -f "$path" ]; then
        echo "[restore] backup file not found: $path" >&2
        exit 1
    fi
    echo "[restore] copying $path into $REDIS_DATA_DIR/dump.rdb"
    echo "[restore] NOTE: redis must be restarted (docker compose restart redis) to load this snapshot"
    cp "$path" "$REDIS_DATA_DIR/dump.rdb"
    echo "[restore] Redis snapshot staged"
}

case "$TARGET" in
    mariadb) restore_mariadb ;;
    redis) restore_redis ;;
    *)
        echo "usage: restore.sh [mariadb|redis] [backup_filename]" >&2
        exit 1
        ;;
esac
