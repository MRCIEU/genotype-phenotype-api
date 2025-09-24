#!/bin/bash
set -e

sudo docker compose up certbot
sudo docker compose down
sudo docker compose up -d --remove-orphans
