# Evaluation demo guide

How to demonstrate each module live. Run `make up` once first — every demo below assumes the full stack is already running and seeded (`make up` does both).

```bash
git clone https://github.com/farmer0010/ft_transcendence.git
cd ft_transcendence
make up
```

Fill in real values in `.env` beforehand for anything that needs a real external credential (OAuth login, Slack); everything below that doesn't touch those works with the placeholder `.env.example` values as-is.

---

## Prerequisite fixes (not a module on their own, but load-bearing for the rest)

1. **Actuator health was previously admin-only, so neither Docker healthchecks nor Prometheus could reach it.**
   ```bash
   curl http://localhost/swagger-ui/index.html   # nginx still blocks /actuator externally either way
   docker compose exec backend curl -s http://localhost:8080/actuator/health
   docker compose exec prometheus wget -qO- http://localhost:9090/api/v1/targets
   ```
   Expected: the actuator call returns `{"status":"UP",...}`; the Prometheus targets call shows `"job":"cabinet-backend"` with `"health":"up"`.

2. **Seed idempotency.** Run `make seed` twice in a row — the second run should finish cleanly (`시드를 넣었습니다.`) instead of failing on a duplicate-key error.

---

## Module A — ELK log management (Major)

1. Open Kibana: `http://localhost:5601`, log in as `elastic` / `$ELASTIC_PASSWORD` (from `.env`).
2. Go to **Dashboards → App Logs Overview** — it was auto-imported on boot. It should show panels for error count over time, log level distribution, and log volume by service, with live data (cabinets were just seeded, generating backend log traffic).
3. Generate some traffic and confirm it lands within seconds:
   ```bash
   for i in 1 2 3; do curl -s http://localhost/v4/cabinets/status-summary/all >/dev/null; done
   docker compose exec -T elasticsearch curl -s -u "elastic:$ELASTIC_PASSWORD" \
     "http://localhost:9200/app-logs/_search?q=service:nginx&size=1&sort=@timestamp:desc"
   ```
4. Security: try Kibana with a wrong password — it should reject. Try reaching Elasticsearch from the host: `curl http://localhost:9200` should fail to connect (no port published).
5. Retention: `docker compose exec -T elasticsearch curl -s -u "elastic:$ELASTIC_PASSWORD" http://localhost:9200/_ilm/policy/app-logs-ilm-policy` — shows the rollover (1d/1gb) and delete (`LOG_RETENTION_DAYS`, default 30) phases.

## Module B — backend as microservices (Major)

1. Show the two independent services: `docker compose ps backend notification-service` — separate containers, separate images, separate healthchecks.
2. Trigger an alarm end to end without needing a real Slack token — push a message directly onto the stream the backend would publish to, and watch notification-service pick it up:
   ```bash
   docker compose exec redis redis-cli XADD slack-alarm-stream '*' intraId demo message "demo alarm"
   docker compose logs notification-service --tail 5
   docker compose exec redis redis-cli XPENDING slack-alarm-stream cabinet-backend-group
   docker compose exec redis redis-cli XLEN slack-alarm-stream
   ```
   Expected: notification-service logs show it received the message and attempted the Slack call (fails with `invalid_auth` on a placeholder token — that's expected and fine, the point is it was consumed, acked, and deleted). `XPENDING` is empty and `XLEN` only has the permanent `init` placeholder entry.
3. Show the backend never imports anything Slack-related: `grep -r Slack backend/src/main/java/com/gyeongsan/cabinet/alarm/` returns nothing (the Slack classes live under `notification-service/`, not `backend/`).

## Module C — health checks / status page / automated backup + DR (Minor)

1. `docker compose ps` — every service shows `(healthy)`.
2. Status page: `http://localhost:3001`, log in with `UPTIME_KUMA_ADMIN_USER`/`UPTIME_KUMA_ADMIN_PASSWORD`. Monitors for backend/ai/nginx/mariadb/redis should already exist and show green.
3. Backup: `make backup`, then `ls backups/mariadb backups/redis` — new timestamped files appear.
4. Disaster recovery rehearsal (the real test — this actually wipes and restores the database):
   ```bash
   make dr-test
   ```
   Expected output ends with `PASS: cabinet count matches before (304) and after restore (304)`.
5. Restore a specific backup: `make restore TARGET=mariadb FILE=<name from backups/mariadb/>`.

## Module D — data export/import (Minor)

Requires an ADMIN session cookie/JWT — easiest via the live site or by promoting a locally-created test account to `ADMIN` in the DB. All examples below assume `$ADMIN_TOKEN` holds a valid JWT for an ADMIN user.

```bash
AUTH="Authorization: Bearer $ADMIN_TOKEN"

# Export, all three formats
curl -s -H "$AUTH" "http://localhost/v4/admin/data/export/cabinets?format=json" | head -c 200
curl -s -H "$AUTH" "http://localhost/v4/admin/data/export/cabinets?format=csv" | head -3
curl -s -H "$AUTH" "http://localhost/v4/admin/data/export/cabinets?format=xml" | head -c 200

# Import, happy path
echo '[{"visibleNum":9501,"status":"AVAILABLE","lentType":"PRIVATE","maxUser":1,"floor":9,"section":"Z","row":1,"col":1}]' > /tmp/ok.json
curl -s -H "$AUTH" -F "file=@/tmp/ok.json;type=application/json" \
  "http://localhost/v4/admin/data/import/cabinets?format=json"
# -> {"data":{"totalRows":1,"successCount":1,"failureCount":0,"errors":[]}}

# Import, validation failure (duplicate + invalid enum) - nothing gets persisted
echo '[{"visibleNum":9501,"status":"AVAILABLE","lentType":"PRIVATE","maxUser":1},{"visibleNum":9999,"status":"NOT_REAL","lentType":"PRIVATE","maxUser":1}]' > /tmp/bad.json
curl -s -H "$AUTH" -F "file=@/tmp/bad.json;type=application/json" \
  "http://localhost/v4/admin/data/import/cabinets?format=json"
# -> HTTP 400, data.errors has 2 entries, data.successCount is 0

# No permission (a non-admin JWT, or no token at all)
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost/v4/admin/data/export/cabinets?format=json"
# -> 401
```

## Module E — single-command execution

```bash
rm -rf .env fe/.env db_data redis_data backups   # simulate a clean clone
make up
```
Expected: one command, no manual steps, ends with the full URL list (FE/API/Swagger/Grafana/Kibana/Uptime Kuma) and the stack already seeded (`make check` right after returns `"totalCounts":304`). Re-running `make up` again should behave the same way (idempotent) with no 502s from nginx.
