# ValPark boîtier — connexions / pinout

Hardware cible : **Raspberry Pi Zero 2 WH** (header 40 broches déjà soudé),
**Waveshare SIM7600G-H 4G HAT (B)** (SKU 19485), **GY-521 MPU-6050**,
**Waveshare 2.9" e-Paper Module B/W** (SKU 12956, 296×128), batterie externe 20 000 mAh.

Sources : wiki et manuels officiels Waveshare
([SK 12956](https://www.waveshare.com/wiki/2.9inch_e-Paper_Module_Manual),
[SIM7600G-H 4G HAT (B)](https://www.waveshare.com/wiki/SIM7600G-H_4G_HAT_(B))).
Ordre des connecteurs documenté, **pas vérifié physiquement** : contrôler la sérigraphie
avant la première mise sous tension.

## Vue d'ensemble

```
Batterie 20 000 mAh
 ├── USB-A #1 ──> Pi PWR (micro-USB alimentation)
 └── USB-A #2 ──> HAT SIM7600 (port micro-USB "USB")

Pi USB (OTG, micro-USB) ──adaptateur OTG micro-A/USB-A──> câble USB-A→micro-B ──> HAT port "USB"
Pi GPIO (header 40 broches) ──> e-paper (SPI) + MPU-6050 (I²C)
```

**Le HAT n'est pas monté sur le Pi.** Ses pogo pins tombent sur les contacts **USB** du
Zero ; monté dessus, il recouvre le header GPIO dont ont besoin l'e-paper et le MPU-6050.
Le HAT reste à côté, relié par câble USB. Les pogo pins ne sont pas utilisés.

## 1. E-paper — Waveshare SKU 12956 ( SPI )

Connecteur 8 broches PH2.0. Ordre documenté : `VCC, GND, DIN, CLK, CS, DC, RST, BUSY`.
SPI mode 0 (CPOL=0, CPHA=0). Pas de MISO sur ce module. Alimentation **3,3 V** (logique du Pi).

| Module | Pi (numéro physique) | BCM | Couleur suggérée |
|---|---|---|---|
| VCC | 1 (3V3) | — | rouge |
| GND | 6 (GND) | — | noir |
| DIN (MOSI) | 19 | GPIO10 | vert |
| CLK (SCLK) | 23 | GPIO11 | jaune |
| CS (CE0) | 24 | GPIO8 | bleu |
| DC | 22 | GPIO25 | orange |
| RST | 11 | GPIO17 | blanc |
| BUSY | 18 | GPIO24 | gris |

Activation : `dtparam=spi=on`. Vérification : `ls /dev/spidev0.0`.
Pilote Python : `waveshare/e-Paper`, classe `epd_2in9` / `epd_2in9_V2` selon l'étiquette
V1/V2/V3 au dos du panneau.

## 2. MPU-6050 — GY-521 ( I²C )

| Module | Pi (numéro physique) | BCM | Note |
|---|---|---|---|
| VCC | 1 (3V3) | — | 3,3 V (le module a un régulateur, mais la logique doit être 3,3 V) |
| GND | 9 (GND) | — | n'importe quelle masse convient |
| SCL | 5 | GPIO3 | I²C1 SCL |
| SDA | 3 | GPIO2 | I²C1 SDA |
| AD0 | non connecté | — | adresse **0x68** (relié à 3V3 → 0x69) |
| INT | non connecté | — | capteur interrogé toutes les minutes |
| XDA, XCL | non connectés | — | I²C auxiliaire inutilisé |

Activation : `dtparam=i2c_arm=on`. Vérification : `i2cdetect -y 1` doit afficher `68`.

## 3. SIM7600G-H 4G HAT (B) — aucun fil GPIO

| Élément | Détail |
|---|---|
| Données | Port **USB** (OTG) du Pi → adaptateur OTG micro-A/USB-A → câble USB-A→micro-B fourni → port **USB** du HAT |
| Alimentation | USB-A #2 de la batterie → port **USB** du HAT (séparé du PWR du Pi) |
| Pogo pins | **Non utilisés** — ne pas poser le HAT sur le Pi |
| Antennes | LTE → `MAIN` (IPEX) ; GNSS → `GNSS` (IPEX) ; `AUX` optionnelle |
| SIM | SIM Sunrise active dans le slot (vérifier le format du slot à réception — le FAQ Waveshare indique SIM standard) |
| Port AT | `/dev/ttyUSB2`, 115200 bauds — vérifier avec `ls /dev/ttyUSB*` |
| LEDs | PWR vert = allumé ; NET clignotant ~1 Hz = enregistré sur le réseau |

Configuration USB host du Pi :
- `/boot/config.txt` (ou `/boot/firmware/config.txt` sous Bookworm) : `dtoverlay=dwc2,dr_mode=host`
- `/boot/cmdline.txt` : supprimer `modules-load=dwc2,g_ether` (le gadget ethernet bloque le HAT)
- Après reboot : `lsusb` doit montrer le hub USB / modem SIM7600.

**Attention VBUS** : le Pi (mode host) et le HAT peuvent tous deux fournir 5 V sur le
même câble USB. Mesurer à la première mise sous tension ; si les deux sources se
rencontrent, utiliser un câble dont le fil VBUS (rouge) est coupé, ou alimenter le HAT
depuis le même rail. Ne pas supposer.

## 4. Réseau (après câblage)

- APN Sunrise : `AT+CGDCONT=1,"IP","internet"` (pas d'identifiant/mot de passe).
- Data via **RNDIS** (`usb0`), recommandé par Waveshare ; si besoin :
  `AT+CUSBPIDSWITCH=9001,1,1`.
- GNSS : `AT+CGPS=1` puis `AT+CGPSINFO` ; antenne à l'extérieur, ~1 min pour le premier fix.
- Vérification API :
  `curl -H "Authorization: Bearer $(cat /etc/valpark/device.token)" http://<SERVER_LAN_IP>:4321/api/device/v1/state`

## 5. Broches utilisées — récapitulatif

| Pi pin | BCM | Usage |
|---|---|---|
| 1 | 3V3 | VCC e-paper + VCC MPU |
| 3 | GPIO2 | SDA (MPU) |
| 5 | GPIO3 | SCL (MPU) |
| 6 | GND | GND e-paper |
| 9 | GND | GND MPU |
| 11 | GPIO17 | RST e-paper |
| 18 | GPIO24 | BUSY e-paper |
| 19 | GPIO10 | DIN/MOSI e-paper |
| 22 | GPIO25 | DC e-paper |
| 23 | GPIO11 | CLK/SCLK e-paper |
| 24 | GPIO8 | CS/CE0 e-paper |

Le port USB (OTG) sert aux données du HAT ; le port PWR à l'alimentation du Pi.
Aucune autre broche GPIO n'est utilisée.
