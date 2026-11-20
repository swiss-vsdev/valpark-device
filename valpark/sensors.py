"""Lectures GNSS (SIM7600 via AT) et accéléromètre (MPU-6050 via I²C)."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


@dataclass
class Sample:
    ts: str | None
    time_source: str  # gnss | ntp | none
    lat: float | None
    lon: float | None
    speed_kmh: float | None
    accel_delta_mg: float  # écart à 1 g
    cpu_temp_c: float | None = None


def _dmm_to_deg(value: str, hemi: str) -> float:
    """ddmm.mmmmm + N/S/E/W → degrés décimaux signés."""
    raw = float(value)
    degrees = math.floor(raw / 100)
    decimal = degrees + (raw - degrees * 100) / 60
    return -decimal if hemi in ("S", "W") else decimal


def parse_cgpsinfo(text: str) -> Sample | None:
    """Parse `+CGPSINFO: lat,N,lon,E,date,time,alt,speed,course`."""
    parts = [part.strip() for part in text.split(",")]
    if len(parts) < 6 or not parts[0] or not parts[2] or not parts[4] or not parts[5]:
        return None
    lat = _dmm_to_deg(parts[0], parts[1])
    lon = _dmm_to_deg(parts[2], parts[3])
    stamp = datetime.strptime(parts[4] + parts[5], "%d%m%y%H%M%S").replace(tzinfo=timezone.utc)
    speed_knots = float(parts[7]) if len(parts) > 7 and parts[7] else 0.0
    return Sample(
        ts=stamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        time_source="gnss",
        lat=round(lat, 6),
        lon=round(lon, 6),
        speed_kmh=round(speed_knots * 1.852, 1),
        accel_delta_mg=0.0,
    )


class Gnss:
    """Modem SIM7600 : GNSS interrogé une fois par minute via AT+CGPSINFO."""

    def __init__(self, port: str):
        import serial

        self.ser = serial.Serial(port, 115200, timeout=2)
        self._at("AT+CGPS=1")

    def _at(self, command: str) -> str:
        self.ser.write((command + "\r\n").encode())
        time.sleep(0.3)
        return self.ser.read(self.ser.in_waiting or 4096).decode(errors="replace")

    def read(self) -> Sample | None:
        output = self._at("AT+CGPSINFO")
        for line in output.splitlines():
            if line.startswith("+CGPSINFO:"):
                return parse_cgpsinfo(line.split(":", 1)[1])
        return None


class MockGnss:
    def read(self) -> Sample | None:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return Sample(stamp, "gnss", 46.227927, 7.357722, 0.0, 0.0)


class Accel:
    """MPU-6050 sur I²C : magnitude du vecteur accélération, écart à 1 g en mg."""

    def __init__(self, bus: int, address: int):
        from smbus2 import SMBus

        self.bus = SMBus(bus)
        self.address = address

    def read_delta_mg(self) -> float:
        data = self.bus.read_i2c_block_data(self.address, 0x3B, 6)
        axes = [int.from_bytes(data[i : i + 2], "big", signed=True) for i in (0, 2, 4)]
        magnitude_g = math.sqrt(sum(axis * axis for axis in axes)) / 16384.0
        return abs(magnitude_g - 1.0) * 1000


class MockAccel:
    def read_delta_mg(self) -> float:
        return 0.0


def make_sensors(cfg: Config):
    if cfg.mock:
        return MockGnss(), MockAccel()
    return Gnss(cfg.gnss_port), Accel(cfg.i2c_bus, cfg.mpu_address)


def cpu_temperature() -> float | None:
    try:
        return int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000
    except (OSError, ValueError):
        return None


def read_sample(gnss, accel) -> Sample:
    """Un échantillon : position GNSS + accel, ou heure de réception si pas de fix."""
    try:
        fix = gnss.read()
    except Exception:
        fix = None
    try:
        delta_mg = accel.read_delta_mg()
    except Exception:
        delta_mg = 0.0

    if fix is None:
        return Sample(None, "none", None, None, None, delta_mg, cpu_temperature())
    fix.accel_delta_mg = delta_mg
    fix.cpu_temp_c = cpu_temperature()
    return fix
