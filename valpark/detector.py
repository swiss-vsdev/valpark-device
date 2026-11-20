"""Machine d'états : décider quand émettre PARKED / DEPARTED / HEARTBEAT."""
from __future__ import annotations

import time

from .config import Config
from .sensors import Sample


class Detector:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.calm_count = 0
        self.parked = False
        self.last_heartbeat = time.monotonic()

    def update(self, sample: Sample) -> list[str]:
        cfg = self.cfg
        now = time.monotonic()
        speed = sample.speed_kmh
        calm = (speed is None or speed <= cfg.calm_speed_kmh) and (
            sample.accel_delta_mg <= cfg.calm_accel_mg
        )
        moving = (speed is not None and speed >= cfg.moving_speed_kmh) or (
            sample.accel_delta_mg >= cfg.moving_accel_mg
        )

        events: list[str] = []
        if not self.parked:
            if calm:
                self.calm_count += 1
                if self.calm_count >= cfg.calm_samples:
                    self.parked = True
                    events.append("PARKED")
            else:
                self.calm_count = 0
                if now - self.last_heartbeat >= cfg.heartbeat_s:
                    self.last_heartbeat = now
                    events.append("HEARTBEAT")
        elif moving:
            self.parked = False
            self.calm_count = 0
            events.append("DEPARTED")
        return events
