#!/bin/bash
set -euo pipefail

#Add this to the crontab on the server running the API
# 30 6 * * * flock -n /tmp/gpmap-refresh-ssl.lock /home/opc/genotype-phenotype-api/refresh_ssl_certs.sh >> /var/log/gpmap-refresh-ssl.log 2>&1

sudo docker service scale gpmap_certbot=1
sleep 10
sudo docker service update --force gpmap_frontend
