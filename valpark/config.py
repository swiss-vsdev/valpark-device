"""Configuration du boîtier. Aucun secret dans ce fichier."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path("/etc/valpark/config.toml")


@dataclass
class Config:
    server_base: str = "http://localhost:4321"
    token_path: Path = Path("/etc/valpark/device.token")
    db_path: Path = Path("/var/lib/valpark/events.sqlite3")

    mock: bool = True  # legacy: used as fallback for both flags below
    mock_sensors: bool | None = None
    mock_display: bool | None = None

    @property
    def sensors_mocked(self) -> bool:
        return self.mock if self.mock_sensors is None else self.mock_sensors

    @property
    def display_mocked(self) -> bool:
        return self.mock if self.mock_display is None else self.mock_display

    gnss_port: str = "/dev/ttyUSB2"
    i2c_bus: int = 1
    mpu_address: int = 0x68
    epd_model: str = "epd_2in9_V2"
    vendor_dir: Path = Path("/opt/valpark/vendor/e-Paper/RaspberryPi_JetsonNano/python/lib")

    sample_interval_s: int = 60
    calm_samples: int = 2
    calm_speed_kmh: float = 2.0
    calm_accel_mg: float = 100.0
    moving_speed_kmh: float = 10.0
    moving_accel_mg: float = 300.0
    heartbeat_s: int = 300

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        p = Path(path or os.getenv("VALPARK_CONFIG", DEFAULT_PATH))
        cfg = cls()
        if not p.is_file():
            return cfg
        with p.open("rb") as fh:
            data = tomllib.load(fh)

        server = data.get("server", {})
        hw = data.get("hardware", {})
        detection = data.get("detection", {})
        paths = data.get("paths", {})

        cfg.server_base = server.get("base", cfg.server_base)
        cfg.token_path = Path(server.get("token_path", cfg.token_path))
        cfg.mock = bool(hw.get("mock", cfg.mock))
        for key in ("mock_sensors", "mock_display"):
            if key in hw:
                setattr(cfg, key, bool(hw[key]))
        cfg.gnss_port = hw.get("gnss_port", cfg.gnss_port)
        cfg.i2c_bus = int(hw.get("i2c_bus", cfg.i2c_bus))
        mpu_address = hw.get("mpu_address", cfg.mpu_address)
        cfg.mpu_address = int(mpu_address, 0) if isinstance(mpu_address, str) else int(mpu_address)
        cfg.epd_model = hw.get("epd_model", cfg.epd_model)
        cfg.vendor_dir = Path(hw.get("vendor_dir", cfg.vendor_dir))

        cfg.sample_interval_s = int(detection.get("sample_interval_s", cfg.sample_interval_s))
        cfg.calm_samples = int(detection.get("calm_samples", cfg.calm_samples))
        cfg.calm_speed_kmh = float(detection.get("calm_speed_kmh", cfg.calm_speed_kmh))
        cfg.calm_accel_mg = float(detection.get("calm_accel_mg", cfg.calm_accel_mg))
        cfg.moving_speed_kmh = float(detection.get("moving_speed_kmh", cfg.moving_speed_kmh))
        cfg.moving_accel_mg = float(detection.get("moving_accel_mg", cfg.moving_accel_mg))
        cfg.heartbeat_s = int(detection.get("heartbeat_s", cfg.heartbeat_s))

        cfg.db_path = Path(paths.get("db", cfg.db_path))
        return cfg
