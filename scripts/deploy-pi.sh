#!/usr/bin/env bash
# Deploy Wall-A Pi application to the Raspberry Pi over SSH.
# Usage: ./scripts/deploy-pi.sh

set -euo pipefail

PI_HOST="austin@pi5.local"
PI_DIR="~/wall-a"

echo "Deploying to $PI_HOST:$PI_DIR ..."

rsync -avz --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'firmware/' \
    --exclude 'server/' \
    --exclude 'hardware/' \
    . "$PI_HOST:$PI_DIR/"

echo "Installing Pi package..."
ssh "$PI_HOST" "cd $PI_DIR/pi && pip install -e ."

echo "Done! Run with: ssh $PI_HOST 'walla'"
