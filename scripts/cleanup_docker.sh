#!/bin/bash
set -e

# Cron on the Swarm manager (same directory as stack deploy):
# 0 7 * * 0 flock -n /tmp/gpmap-cleanup-docker.lock /home/opc/genotype-phenotype-api/scripts/cleanup_docker.sh >> /var/log/gpmap-cleanup-docker.log 2>&1

echo "Cleaning up old docker images and containers"
sudo docker image prune -a -f
sudo docker container prune -f -a
sudo docker builder prune -f

echo "Done"