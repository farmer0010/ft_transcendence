# README additions — bonus module justification (draft)

This is the detailed version of the "Bonus modules" section now in the root `README.md`. It exists separately so the reasoning behind each module — what was implemented, what deliberately wasn't, and why — can be read without scrolling past the rest of the README.

## Infrastructure for log management (ELK) — Major, 2 points

**Why this module.** The stack has three independently-deployed services that each produce their own logs (backend, notification-service, nginx). Debugging an issue that spans a request through nginx into the backend and out to notification-service previously meant reading three separate `docker compose logs` streams by hand with no shared correlation key.

**What was implemented.**
- Elasticsearch, Logstash, and Kibana, pinned to 8.15.3.
- A per-request `traceId` (backend, via `TraceIdFilter` + MDC) on every structured log line, so a single request can be traced across log entries from the same service.
- `logstash-logback-encoder`'s `LogstashTcpSocketAppender` streams structured JSON straight from backend/notification-service to Logstash. nginx writes a JSON access log to a shared Docker volume that Logstash tails with a `file` input. Both choices were picked over Docker's `gelf`/`syslog` logging drivers specifically because those run in the Docker **daemon's** network namespace, not the container's, and can't resolve compose service DNS names like `logstash` — see `docs/architecture.md` for the full reasoning.
- Security: `xpack.security` enabled, three separate accounts (`elastic` superuser for Kibana login, the built-in `kibana_system` user, and a custom `logstash_writer` role scoped to write-only on `app-logs*` — Logstash never uses the superuser). Only Kibana's port is published to the host.
- Retention: an ILM policy (`app-logs-ilm-policy`) rolls the write index over at 1 day/1GB and deletes indices older than `LOG_RETENTION_DAYS` (default 30).
- A Kibana dashboard ("App Logs Overview": error count over time, log level distribution, log volume by service) built against the live stack via the Kibana API and exported to `elk/kibana/saved_objects/dashboard.ndjson`, auto-imported by a one-shot init container on every `make up`.

**What was deliberately left out.** `ai` service logs aren't collected. It only uses bare `print()`/uvicorn's default stdout logging today; the only way to collect that without adding real logging to the service first would be mounting the host's Docker log directory into Logstash, which is tied to container IDs that change on every recreate. Also, retention is delete-only — there's no snapshot/archive step beyond the ILM delete phase, since that would need a configured snapshot repository (e.g. object storage) that doesn't exist in this setup.

## Backend as microservices — Major, 2 points

**Why this module.** Before this, the entire backend ran as one Spring Boot process, including Slack delivery — an external dependency with its own failure mode (rate limits, outages, auth errors) that has nothing to do with the locker/rental domain.

**What was implemented.** `notification-service`: a standalone Spring Boot app, own `Dockerfile`, own compose entry, own healthcheck (`/actuator/health`). It consumes the `slack-alarm-stream` Redis Stream (consumer group `cabinet-backend-group`, same name used before the split so pending entries carried over cleanly) and is the *only* service that calls the Slack API. The backend only publishes to that stream (`AlarmEventHandler`, unchanged) and keeps consuming the unrelated `logtime-sync-stream` itself. A dedup guard (`SETNX` on the stream record ID, 24h TTL) prevents a redelivered message (consumer crash before ack) from being sent to Slack twice.

**What was deliberately left out.** No API gateway or service mesh — with two backend-side services talking over one Redis Stream, that would be complexity without a corresponding benefit at this scale. `AdminAlarmService`'s emergency-notice feature was changed to publish through the same event path instead of calling Slack synchronously (it previously worked via leftover `OSIV`-held sessions with no real transaction boundary); it's now `@Transactional(readOnly = true)` so the `AFTER_COMMIT` event listener actually fires. See `docs/architecture.md` for the full event flow and schema.

## Health check/status page with automated backups and DR — Minor, 1 point

**Why this module.** A status page or a backup job that nobody has watched actually recover from a failure is a false sense of safety, not a safety net.

**What was implemented.**
- A Docker `healthcheck` on every service (mariadb, redis, backend, notification-service, ai, nginx, fe, prometheus, grafana, elasticsearch, logstash, kibana, uptime-kuma, backup), and `depends_on: condition: service_healthy` throughout, so the stack actually comes up in dependency order instead of racing.
- Uptime Kuma, with a one-shot container that auto-provisions monitors for backend/ai/nginx/mariadb/redis on first boot (idempotent — re-running it skips monitors that already exist).
- A `backup` service that runs `mariadb-dump --single-transaction` (gzipped) and a Redis `BGSAVE`+copy on a schedule (`BACKUP_INTERVAL_SECONDS`, default daily) and on demand (`make backup`), pruning to the newest `BACKUP_RETENTION_COUNT` files (default 7).
- `make restore` and `make dr-test`: the latter actually runs backup → wipes the database (`DROP DATABASE`/`CREATE DATABASE`) → restores → compares the `cabinet` row count before and after, and prints PASS/FAIL. This was run against a freshly seeded database (304 cabinets) and passed.

**What was deliberately left out.** Backups live in a local `backups/` volume only; nothing syncs them off-host, so a full host-loss scenario isn't actually recoverable yet (documented as a known limitation in `docs/disaster-recovery.md`, not hidden).

## Data export and import — Minor, 1 point

**Why this module.** Admins had no way to get locker/rental/coin data out for analysis, or to bulk-load lockers without writing SQL directly against production.

**What was implemented.** `/v4/admin/data/export/{cabinets,lent-histories,coin-histories}?format=json|csv|xml`, each writing straight to the HTTP response's `OutputStream` instead of building the serialized payload in memory first. `lent-histories`/`coin-histories` rows expose only the user's intra name — no email, role, or tokens. `/v4/admin/data/import/cabinets` (`?format=json|csv`) validates every row before persisting anything: if any row fails (missing field, invalid `CabinetStatus`/`LentType`, duplicate `visibleNum` against the file or the table), nothing is inserted and every failing row is reported, not just the first. A zero-error file is inserted in a single `saveAll`.

**What was deliberately left out.** Import only supports lockers (as scoped: "최소한 락커"), not rental/coin history, and XML isn't an accepted import format (only an export one) — accepting XML uploads wasn't asked for and would have doubled the parsing surface for no requested benefit.

## Single-command execution

`make up` now builds the backend and notification-service JARs, builds the FE, brings up every container with `docker compose up --wait` (health-gated), runs the one-shot init containers (Uptime Kuma provisioning, the ELK setup, the Kibana dashboard import) as a separate step — `docker compose up --wait` was found to misreport failure when more than one one-shot container exits 0 in the same batch — then seeds the 304 lockers (idempotent, via `INSERT IGNORE`) and runs a smoke check. Verified by deleting `.env`/`fe/.env`/`db_data`/`redis_data`/`backups` (a true clean-clone state) and running `make up` repeatedly.
