#!/bin/sh
set -eu

ES_URL="http://elasticsearch:9200"
AUTH="elastic:${ELASTIC_PASSWORD}"

echo "[elk-setup] waiting for Elasticsearch..."
i=0
until curl -fsS -u "$AUTH" "$ES_URL/_cluster/health" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
        echo "[elk-setup] Elasticsearch did not become reachable in time" >&2
        exit 1
    fi
    sleep 2
done
echo "[elk-setup] Elasticsearch is reachable"

echo "[elk-setup] setting kibana_system password"
curl -fsS -u "$AUTH" -X POST "$ES_URL/_security/user/kibana_system/_password" \
    -H 'Content-Type: application/json' \
    -d "{\"password\":\"${KIBANA_SYSTEM_PASSWORD}\"}"
echo

echo "[elk-setup] creating least-privilege logstash_writer role"
curl -fsS -u "$AUTH" -X PUT "$ES_URL/_security/role/logstash_writer" \
    -H 'Content-Type: application/json' \
    -d '{
        "cluster": ["manage_index_templates", "monitor"],
        "indices": [
            {
                "names": ["app-logs*"],
                "privileges": ["create_index", "write", "manage"]
            }
        ]
    }'
echo

echo "[elk-setup] creating logstash_writer user"
curl -fsS -u "$AUTH" -X POST "$ES_URL/_security/user/logstash_writer" \
    -H 'Content-Type: application/json' \
    -d "{\"password\":\"${LOGSTASH_WRITER_PASSWORD}\",\"roles\":[\"logstash_writer\"]}"
echo

echo "[elk-setup] creating ILM policy app-logs-ilm-policy (hot rollover 1d/1gb, delete after ${LOG_RETENTION_DAYS:-30}d)"
curl -fsS -u "$AUTH" -X PUT "$ES_URL/_ilm/policy/app-logs-ilm-policy" \
    -H 'Content-Type: application/json' \
    -d "{
        \"policy\": {
            \"phases\": {
                \"hot\": {
                    \"actions\": {
                        \"rollover\": {
                            \"max_age\": \"1d\",
                            \"max_primary_shard_size\": \"1gb\"
                        }
                    }
                },
                \"delete\": {
                    \"min_age\": \"${LOG_RETENTION_DAYS:-30}d\",
                    \"actions\": { \"delete\": {} }
                }
            }
        }
    }"
echo

echo "[elk-setup] creating index template app-logs-template"
curl -fsS -u "$AUTH" -X PUT "$ES_URL/_index_template/app-logs-template" \
    -H 'Content-Type: application/json' \
    -d '{
        "index_patterns": ["app-logs-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index.lifecycle.name": "app-logs-ilm-policy",
                "index.lifecycle.rollover_alias": "app-logs"
            },
            "mappings": {
                "properties": {
                    "@timestamp": { "type": "date" },
                    "service": { "type": "keyword" },
                    "level": { "type": "keyword" },
                    "traceId": { "type": "keyword" },
                    "message": { "type": "text" },
                    "logger_name": { "type": "keyword" },
                    "status": { "type": "integer" },
                    "method": { "type": "keyword" },
                    "uri": { "type": "keyword" }
                }
            }
        }
    }'
echo

echo "[elk-setup] checking whether the app-logs write alias already exists"
if curl -fsS -u "$AUTH" "$ES_URL/_alias/app-logs" >/dev/null 2>&1; then
    echo "[elk-setup] app-logs alias already exists, skipping bootstrap index creation"
else
    echo "[elk-setup] bootstrapping initial index app-logs-000001"
    curl -fsS -u "$AUTH" -X PUT "$ES_URL/app-logs-000001" \
        -H 'Content-Type: application/json' \
        -d '{
            "aliases": {
                "app-logs": { "is_write_index": true }
            }
        }'
    echo
fi

echo "[elk-setup] done"
