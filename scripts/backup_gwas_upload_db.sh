#!/bin/bash
set -euo pipefail

API_SERVICE_NAME="${GPMAP_API_SERVICE_NAME:-gpmap_api}"
BACKUP_MODULE="app.backup_gwas_upload_db"

API_CONTAINER="$(docker ps -q -f "name=${API_SERVICE_NAME}" | head -n 1)"
if [[ -z "$API_CONTAINER" ]]; then
  echo "No running ${API_SERVICE_NAME} container found; skipping OCI backup."
  exit 0
fi

echo "Running GWAS upload database backup in container ${API_CONTAINER}"
docker exec "$API_CONTAINER" python -m "$BACKUP_MODULE"
