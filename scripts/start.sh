#!/usr/bin/env sh
# Production start (Railway). Local dev still uses: uvicorn backend.app:app --reload --port 8000
# See docs/DEPLOY.md.
set -u

# Keep everything stateful on the persistent volume.
VOL="${RAILWAY_VOLUME_MOUNT_PATH:-}"
if [ -n "$VOL" ]; then
  export SIKHNET_DB="${SIKHNET_DB:-$VOL/community.db}"
  export SIKHNET_DATA="${SIKHNET_DATA:-$VOL/qa.jsonl}"
fi
DATA="${SIKHNET_DATA:-data/processed/qa.jsonl}"

# Dataset: fetched once from a private URL, then ingested. SIKHNET_REINGEST=1 forces a refresh.
if [ -n "${SIKHNET_DATA_URL:-}" ] && { [ ! -s "$DATA" ] || [ "${SIKHNET_REINGEST:-0}" = "1" ]; }; then
  mkdir -p "$(dirname "$DATA")"
  RAW="$(dirname "$DATA")/raw-dataset.${SIKHNET_DATA_FORMAT:-jsonl}"
  if python3 scripts/fetch_dataset.py "$RAW"; then
    python3 ingest/ingest.py "$RAW" --out "$DATA" --source "${SIKHNET_DATA_SOURCE:-sikhnet-qa-dataset}" \
      || echo "start: ingest failed; serving whatever data is available" >&2
  else
    echo "start: dataset download failed; serving whatever data is available" >&2
  fi
fi
[ -s "$DATA" ] || echo "start: WARNING no dataset at $DATA, serving the 4-entry sample. Check /api/health." >&2

# One worker on purpose: community storage is a single SQLite file.
exec uvicorn backend.app:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
