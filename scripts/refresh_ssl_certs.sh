#!/bin/bash
set -euo pipefail

sudo docker service scale gpmap_certbot=1
sleep 10
sudo docker service update --force gpmap_frontend