#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Cron on the Swarm manager (same directory as stack deploy):
# 30 6 * * * flock -n /tmp/gpmap-refresh-ssl.lock /home/opc/genotype-phenotype-api/scripts/refresh_ssl_certs.sh >> /var/log/gpmap-refresh-ssl.log 2>&1

cd "${STACK_DIR}"

# One-shot renew (do not use `docker service scale` — certbot exits and Swarm never stabilizes).
sudo docker run --rm \
  -v "${STACK_DIR}/certbot/webroot:/var/www/certbot" \
  -v "${STACK_DIR}/certbot/letsencrypt:/etc/letsencrypt" \
  --network gpmap_network \
  certbot/certbot renew --webroot --webroot-path=/var/www/certbot

FRONTEND_CONTAINER=$(sudo docker ps -q -f name=gpmap_frontend | head -1)
if [[ -z "${FRONTEND_CONTAINER}" ]]; then
  echo "No running gpmap_frontend container found" >&2
  exit 1
fi
sudo docker exec "${FRONTEND_CONTAINER}" nginx -s reload
