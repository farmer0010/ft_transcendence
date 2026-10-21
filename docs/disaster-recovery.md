# Disaster Recovery

## What's backed up

| Component | Mechanism | Where |
|---|---|---|
| MariaDB (`cabi`) | `mariadb-dump --single-transaction` piped through `gzip` | `backups/mariadb/cabi_<timestamp>.sql.gz` |
| Redis | `redis-cli BGSAVE`, then the resulting `dump.rdb` is copied out | `backups/redis/dump_<timestamp>.rdb` |

Both are produced by `backup/scripts/backup.sh`, running inside the `backup` service (`backup/Dockerfile`, based on `mariadb:10.6` + `redis-tools`). The service loops forever (`backup/scripts/entrypoint.sh`), running a backup every `BACKUP_INTERVAL_SECONDS` (default: 86400s / daily), and also backs up once immediately on startup. Each run prunes old backups down to the newest `BACKUP_RETENTION_COUNT` files per component (default: 7), so the `backups/` volume doesn't grow unbounded.

Both env vars are optional and documented in `.env.example`.

## On-demand backup

```bash
make backup
```

Runs `backup.sh` once against the currently running stack. Files land under `backups/mariadb/` and `backups/redis/` on the host (bind-mounted, not inside the container).

## Restore

```bash
make restore                               # restores MariaDB from the newest backup
make restore TARGET=redis                  # restores Redis from the newest backup
make restore TARGET=mariadb FILE=cabi_20260101_030000.sql.gz   # restore a specific file
```

- **MariaDB**: `restore.sh` drops and recreates the `cabi` schema, then replays the dump. The backend keeps old DB connections open in its connection pool across a DB-level restore, so **restart the backend afterwards** (`docker compose restart backend`) to force it to reconnect with a clean pool.
- **Redis**: the chosen `.rdb` file is copied into the live `redis_data` volume as `dump.rdb`. Redis only loads an RDB file at startup, so **restart Redis afterwards** (`docker compose restart redis`) to actually load it.

## Automated DR rehearsal

```bash
make dr-test
```

`scripts/dr-test.sh` proves the backup/restore path actually works, end to end:

1. Records the current row count of the `cabinet` table (refuses to continue if it's empty — seed first with `make seed`).
2. Takes a fresh backup (`make backup` equivalent).
3. **Wipes the database** (`DROP DATABASE cabi; CREATE DATABASE cabi;`) — simulating total data loss.
4. Restores from the backup taken in step 2.
5. Re-counts `cabinet` rows and compares against step 1. Prints `PASS`/`FAIL` and exits non-zero on mismatch.

This has been run against a freshly seeded database (304 cabinets) and passes: count before = count after = 304.

## Failure scenarios and recovery steps

### MariaDB data corruption / accidental data loss
1. `make restore` (defaults to the newest MariaDB backup), or `make restore FILE=<name>` for a specific point in time.
2. `docker compose restart backend` to drop stale pooled connections.
3. Verify with `make check` (public cabinet-status endpoint) and a logged-in smoke test of rental/return.

### Redis data loss (cache state only — not the source of truth)
1. `make restore TARGET=redis` then `docker compose restart redis`.
2. Redis here mainly holds reservation caching, ShedLock locks, and the Slack/logtime streams; a full loss is recoverable without data integrity risk to MariaDB-backed entities, at worst some in-flight distributed locks and un-consumed stream messages are lost.

### Full container/host loss (e.g. the Docker host disk is gone)
1. Provision a new host with Docker/Docker Compose.
2. Restore the repository from git and the `backups/` directory from off-host storage (the `backups/` directory itself is **not** replicated anywhere by this project yet — see "Known limitation" below).
3. `make up` to rebuild and start every service from a clean state.
4. Once MariaDB/Redis are healthy, run the restore steps above using the recovered `backups/` directory.

### Single service crash-looping
1. `docker compose ps` to see which service is reported unhealthy (every service now has a Docker healthcheck, see `docker-compose.yml`).
2. `docker compose logs <service>` to read the failure.
3. `docker compose restart <service>` or `make up` to rebuild if the image itself needs a fix.
4. The Uptime Kuma status page (`http://localhost:3001`) shows the same information visually and keeps history of when a service went down.

## Known limitation

Backups are written to the local `backups/` directory (bind-mounted from the host), which is **not** copied off-host automatically. For the "full container/host loss" scenario to be truly recoverable, `backups/` needs to be synced to external storage (e.g. object storage) on a schedule — that step is out of scope for this module and would be a natural follow-up.
