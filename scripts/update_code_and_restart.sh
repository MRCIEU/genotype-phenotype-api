#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down
sudo docker compose up -d --remove-orphans

# immediately populate cache
curl http://localhost:8000/v1/info/gpmap_metadata
curl http://localhost:8000/v1/search/options