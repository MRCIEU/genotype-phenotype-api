#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose down
sudo docker compose up certbot -d
sudo docker compose up -d --remove-orphans
