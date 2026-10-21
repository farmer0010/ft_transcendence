#!/bin/sh
set -eu

KIBANA_URL="http://kibana:5601"
AUTH="elastic:${ELASTIC_PASSWORD}"

echo "[kibana-setup] importing saved objects (data view + visualizations + dashboard)"
curl -fsS -u "$AUTH" -X POST "$KIBANA_URL/api/saved_objects/_import?overwrite=true" \
    -H "kbn-xsrf: true" \
    --form file=@/saved_objects/dashboard.ndjson
echo
echo "[kibana-setup] done"
