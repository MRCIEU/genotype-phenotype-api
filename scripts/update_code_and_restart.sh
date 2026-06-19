#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune --detach=true

sleep 10
"$SCRIPT_DIR/backup_gwas_upload_db.sh"
