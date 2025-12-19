#!/bin/bash
set -e

sudo docker stack rm gpmap
sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune
