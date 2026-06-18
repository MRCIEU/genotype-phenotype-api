#!/bin/bash
set -euo pipefail

ENV_FILE="/home/opc/genotype-phenotype-api/.env.backend"
DB_PATH="/home/opc/gpmap_data/db/gwas_upload.db"
BACKUP_PREFIX="db_backups/gwas_upload"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

DB_PATH="${GWAS_UPLOAD_DB_PATH:-$DB_PATH}"

if [[ ! -f "$DB_PATH" ]]; then
  echo "GWAS upload database not found at $DB_PATH; skipping OCI backup."
  exit 0
fi

if [[ -z "${OCI_NAMESPACE:-}" || -z "${OCI_BUCKET_NAME:-}" ]]; then
  echo "OCI_NAMESPACE and OCI_BUCKET_NAME must be set in .env.backend" >&2
  exit 1
fi

if ! command -v oci >/dev/null 2>&1; then
  echo "oci CLI not found on PATH" >&2
  exit 1
fi

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
OBJECT_NAME="${BACKUP_PREFIX}/gwas_upload_${TIMESTAMP}.db"
BACKUP_COPY="$(mktemp /tmp/gwas_upload_backup.XXXXXX.db)"
trap 'rm -f "$BACKUP_COPY"' EXIT

cp "$DB_PATH" "$BACKUP_COPY"

echo "Uploading $DB_PATH to oci://${OCI_BUCKET_NAME}/${OBJECT_NAME}"
oci os object put \
  --auth instance_principal \
  --namespace "$OCI_NAMESPACE" \
  --bucket-name "$OCI_BUCKET_NAME" \
  --file "$BACKUP_COPY" \
  --name "$OBJECT_NAME" \
  --force

echo "GWAS upload database backed up to ${OBJECT_NAME}"
