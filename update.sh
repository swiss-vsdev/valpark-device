#!/usr/bin/env bash
# Mise à jour simple : git pull + dépendances + redémarrage du service.
set -euo pipefail

APP_DIR=/opt/valpark
cd "$APP_DIR"
sudo git pull --ff-only
sudo "$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
sudo systemctl restart valpark
echo "mis à jour — journalctl -u valpark -f"
