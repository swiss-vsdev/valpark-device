#!/usr/bin/env bash
# Mise à jour simple : git pull dans le clone utilisateur, copie vers /opt, restart.
set -euo pipefail

SRC=/home/dietpi/valpark-device
APP_DIR=/opt/valpark

cd "$SRC"
git pull --ff-only
sudo tar -C "$SRC" --exclude=.git --exclude=.venv --exclude=__pycache__ --exclude=vendor -cf - . \
    | sudo tar -C "$APP_DIR" -xf -
sudo "$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
sudo systemctl restart valpark
echo "mis à jour — journalctl -u valpark -f"
