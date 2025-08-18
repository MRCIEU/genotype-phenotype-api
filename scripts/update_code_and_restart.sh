#!/bin/bash
set -e

sudo docker compose pull
sudo docker compose up -d --remove-orphans