#!/usr/bin/env bash
# Installation idempotente sur DietPi (Pi Zero 2 W). À lancer depuis le dépôt cloné.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR=/opt/valpark
CONF_DIR=/etc/valpark
DATA_DIR=/var/lib/valpark

echo "=== paquets ==="
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip python3-smbus i2c-tools git

echo "=== interfaces (SPI, I2C, USB host) ==="
CFG=/boot/firmware/config.txt
CMDLINE=/boot/firmware/cmdline.txt
if [ ! -f "$CFG" ]; then CFG=/boot/config.txt; CMDLINE=/boot/cmdline.txt; fi
for line in 'dtparam=spi=on' 'dtparam=i2c_arm=on' 'dtoverlay=dwc2,dr_mode=host'; do
    grep -qxF "$line" "$CFG" || echo "$line" | sudo tee -a "$CFG" >/dev/null
done
if [ -f "$CMDLINE" ]; then
    sudo sed -i 's/modules-load=dwc2,g_ether//g' "$CMDLINE"
fi
# i2c-dev expose /dev/i2c-1 en espace utilisateur (nécessaire à smbus2)
grep -qxF 'i2c-dev' /etc/modules || echo 'i2c-dev' | sudo tee -a /etc/modules >/dev/null

echo "=== utilisateur et répertoires ==="
id -u valpark >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin valpark
for group in i2c spi gpio; do
    getent group "$group" >/dev/null 2>&1 && sudo usermod -aG "$group" valpark
done
sudo mkdir -p "$APP_DIR" "$CONF_DIR" "$DATA_DIR"

echo "=== copie du code ==="
sudo tar -C "$REPO_DIR" --exclude=.git --exclude=.venv --exclude=__pycache__ --exclude=vendor -cf - . \
    | sudo tar -C "$APP_DIR" -xf -

echo "=== environnement Python ==="
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
sudo "$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "=== pilotes e-paper Waveshare ==="
if [ ! -d "$APP_DIR/vendor/e-Paper" ]; then
    sudo mkdir -p "$APP_DIR/vendor"
    sudo git clone --depth 1 https://github.com/waveshare/e-Paper.git "$APP_DIR/vendor/e-Paper"
fi

echo "=== configuration ==="
if [ ! -f "$CONF_DIR/config.toml" ]; then
    sudo cp "$APP_DIR/config.example.toml" "$CONF_DIR/config.toml"
    echo "  -> $CONF_DIR/config.toml créé (mock=true par défaut)"
fi
sudo chown -R valpark:valpark "$DATA_DIR"
sudo chgrp valpark "$CONF_DIR"

echo "=== service systemd ==="
sudo cp "$APP_DIR/valpark.service" /etc/systemd/system/valpark.service
sudo systemctl daemon-reload
sudo systemctl enable valpark

echo
echo "Installation terminée. Avant de démarrer :"
echo "  1. générer le jeton (npm run device:token dans valpark-website) et le coller dans le portail"
echo "  2. printf 'JETON' | sudo tee $CONF_DIR/device.token"
echo "     sudo chown root:valpark $CONF_DIR/device.token && sudo chmod 640 $CONF_DIR/device.token"
echo "  3. régler $CONF_DIR/config.toml (server.base, hardware.mock=false une fois câblé)"
echo "  4. sudo reboot  (pour activer SPI/I2C/USB host)"
echo "  5. sudo systemctl start valpark && journalctl -u valpark -f"
