#!/bin/bash
set -e

sudo docker service scale gpmap_certbot=1
