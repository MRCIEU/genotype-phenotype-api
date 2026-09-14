#!/bin/bash
set -e

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true

echo "Waiting for API to become healthy"
for i in $(seq 1 100); do
    if curl -sf http://127.0.0.1:8000/health > /dev/null; then
        echo "API is healthy"
        break
    fi
    if [ "$i" -eq 100 ]; then
        echo "API did not become healthy in time" >&2
        exit 1
    fi
    sleep 3
done

bash /home/opc/genotype-phenotype-api/backup_gwas_upload_db.sh
