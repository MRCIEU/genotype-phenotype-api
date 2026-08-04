#!/bin/bash
set -euo pipefail

# Cron on the Swarm manager (same directory as stack deploy):
# 30 6 * * * flock -n /tmp/gpmap-refresh-ssl.lock /home/opc/genotype-phenotype-api/scripts/refresh_ssl_certs.sh >> /var/log/gpmap-refresh-ssl.log 2>&1

REPO_ROOT="/home/opc/genotype-phenotype-api"
cd "${REPO_ROOT}"

# One-shot renew (do not use `docker service scale` — certbot exits and Swarm never stabilizes).
# Paths must match docker-swarm.yml ./certbot mounts (deploy dir = REPO_ROOT).
sudo docker run --rm \
  -v "${REPO_ROOT}/certbot/webroot:/var/www/certbot" \
  -v "${REPO_ROOT}/certbot/letsencrypt:/etc/letsencrypt" \
  --network gpmap_network \
  certbot/certbot renew --webroot --webroot-path=/var/www/certbot

FRONTEND_CONTAINER=$(sudo docker ps -q -f name=gpmap_frontend | head -1)
if [[ -z "${FRONTEND_CONTAINER}" ]]; then
  echo "No running gpmap_frontend container found" >&2
  exit 1
fi
sudo docker exec "${FRONTEND_CONTAINER}" nginx -s reload
