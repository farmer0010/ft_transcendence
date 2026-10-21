#!/bin/sh
set -eu

: "${BACKUP_INTERVAL_SECONDS:=86400}"

echo "[backup] loop starting, interval=${BACKUP_INTERVAL_SECONDS}s"

term() {
    echo "[backup] received signal, exiting loop"
    exit 0
}
trap term TERM INT

while true; do
    if /scripts/backup.sh; then
        echo "[backup] cycle finished ok, sleeping ${BACKUP_INTERVAL_SECONDS}s"
    else
        echo "[backup] cycle failed, will retry after ${BACKUP_INTERVAL_SECONDS}s"
    fi
    sleep "$BACKUP_INTERVAL_SECONDS" &
    wait $!
done
