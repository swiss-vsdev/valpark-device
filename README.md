# ValPark — boîtier (Raspberry Pi / DietPi)

Logiciel embarqué du boîtier de stationnement ValPark. Le Pi reste **bêtement** : il
détecte l'arrêt et le départ, envoie des événements, et affiche ce que le serveur lui
renvoie. Zones, tarifs, sessions et appels Parkingpay sont côté serveur.

Contrat d'API : `../valpark-website/docs/device-api.md` (base `/api/device/v1`).

## Matériel

- Raspberry Pi Zero 2 WH (DietPi)
- Waveshare SIM7600G-H 4G HAT (B) — 4G + GNSS, relié par **USB** (pas de pogo pins)
- GY-521 MPU-6050 sur I²C
- Waveshare 2.9" e-Paper Module B/W (SKU 12956, 296×128) sur SPI
- Batterie externe 20 000 mAh : une sortie USB pour le Pi, une pour le HAT

Câblage complet, pinouts et précautions VBUS : [WIRING.md](WIRING.md).

## Principe

Toutes les minutes : lecture GNSS (`AT+CGPSINFO`) + accéléromètre (I²C).
Deux échantillons calmes consécutifs (~2 min) → `PARKED`. Mouvement soutenu → `DEPARTED`.
`HEARTBEAT` toutes les 5 min en roulant, `BOOT` à chaque démarrage.
Les événements passent par une file SQLite locale avec un `seq` persistant : hors réseau,
ils sont renvoyés dans l'ordre au retour de la connexion, sans doublons.

## Installation sur le Pi (DietPi, SSH)

```bash
ssh dietpi@172.20.10.4          # mot de passe par défaut : raspberry — à changer
git clone <URL_DU_REPO> ~/valpark-device
cd ~/valpark-device
chmod +x install.sh update.sh
./install.sh
```

L'installation est idempotente : paquets, venv Python, pilote e-paper Waveshare, service
systemd, répertoires `/etc/valpark` et `/var/lib/valpark`. Le service n'est **pas** démarré
tant que le jeton n'est pas en place.

## Jeton (une fois)

À générer depuis le dépôt du serveur :

```bash
cd ~/Documents/GitHub/valpark-website && npm run device:token
```

Puis coller le jeton dans le portail (**Configuration → 1. Boîtier**) et l'écrire sur le Pi :

```bash
printf 'LE_JETON' | sudo tee /etc/valpark/device.token >/dev/null
sudo chown root:valpark /etc/valpark/device.token
sudo chmod 640 /etc/valpark/device.token
sudo systemctl start valpark
```

Le serveur ne stocke que le hash du jeton : perdu, il faut en générer un nouveau.

## Configuration

`/etc/valpark/config.toml`, copié depuis `config.example.toml`. Points clés :

- `server.base` — `http://<SERVER_LAN_IP>:4321` en dev, HTTPS en prod
- `hardware.mock = true` — **par défaut** : aucun module nécessaire, l'écran s'affiche
  dans la console. Passer à `false` une fois les modules branchés.
- `detection.*` — seuils et cadence (1 min par échantillon, 2 échantillons calmes)
- `paths.db` — fichier SQLite de la file

## Commandes utiles

```bash
journalctl -u valpark -f                                   # logs
sudo systemctl restart valpark
./update.sh                                                # git pull + pip + restart
python3 -m unittest discover -s tests -v                   # tests (sur le Pi ou en local)
python3 -m valpark.main                                    # exécution manuelle (mock)
```

## Tests sans matériel

Le mode `mock` (config par défaut) simule un capteur immobile avec un fix GNSS et affiche
l'e-paper dans la console. Les tests unitaires couvrent la machine d'états, la file
persistante, le parseur GNSS et le rendu 22 caractères.

## Mises à jour

`update.sh` fait `git pull --ff-only`, réinstalle `requirements.txt` dans le venv, puis
redémarre le service. Pas de OTA signé / A-B : prototype unique.
