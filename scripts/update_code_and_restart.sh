#!/bin/bash
set -e

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune
