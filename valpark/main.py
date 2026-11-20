"""Boucle principale : échantillonner → détecter → envoyer → afficher."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from .api import ApiClient, ApiError, BadRequest
from .config import Config
from .detector import Detector
from .display import Display, apply_state
from .queue import EventQueue
from .sensors import Sample, make_sensors, read_sample

log = logging.getLogger("valpark")


def add_event(queue: EventQueue, event_type: str, sample: Sample) -> None:
    fields: dict = {}
    if sample.lat is not None and sample.lon is not None:
        fields.update(lat=sample.lat, lon=sample.lon)
    if sample.speed_kmh is not None:
        fields["speedKmh"] = sample.speed_kmh
    if sample.cpu_temp_c is not None:
        fields["cpuTempC"] = round(sample.cpu_temp_c, 1)
    queue.add(event_type, ts=sample.ts, time_source=sample.time_source, **fields)


def flush(queue: EventQueue, api: ApiClient, display: Display) -> None:
    events = queue.pending(200)
    if not events:
        return
    seqs = [event["seq"] for event in events]
    try:
        result = api.post_events(events)
    except BadRequest as exc:
        # 400 : le serveur refuse ce lot, ne jamais le renvoyer tel quel.
        log.warning("lot invalide, %d événements abandonnés : %s", len(seqs), exc)
        queue.remove(seqs)
        return
    except (ConnectionError, ApiError) as exc:
        log.warning("envoi différé (%d en file) : %s", queue.size(), exc)
        return
    queue.remove(seqs)
    apply_state(display, result)


def read_token(cfg: Config) -> str:
    """Configuration incomplète → sortie 78 : systemd ne redémarre pas (voir unité)."""
    path = Path(cfg.token_path)
    try:
        token = path.read_text().strip()
    except OSError as exc:
        log.error("jeton introuvable : %s (%s)", path, exc)
        raise SystemExit(os.EX_CONFIG) from exc
    if not token:
        log.error("jeton vide : l'écrire dans %s", path)
        raise SystemExit(os.EX_CONFIG)
    if "<SERVER_LAN_IP>" in cfg.server_base:
        log.error("server.base n'est pas configuré dans %s", os.environ.get("VALPARK_CONFIG", "/etc/valpark/config.toml"))
        raise SystemExit(os.EX_CONFIG)
    return token


def run(cfg: Config) -> None:
    api = ApiClient(cfg.server_base, read_token(cfg))
    queue = EventQueue(cfg.db_path)
    display = Display(cfg)
    gnss, accel = make_sensors(cfg)
    detector = Detector(cfg)

    add_event(queue, "BOOT", Sample(None, "none", None, None, None, 0.0))
    log.info("démarré — mock=%s, serveur=%s", cfg.mock, cfg.server_base)

    next_sample = 0.0
    next_poll = 0.0
    while True:
        now = time.monotonic()
        if now >= next_sample:
            next_sample = now + cfg.sample_interval_s
            try:
                sample = read_sample(gnss, accel)
                for event_type in detector.update(sample):
                    add_event(queue, event_type, sample)
                    log.info("événement %s (file=%d)", event_type, queue.size())
            except Exception:
                log.exception("échantillonnage")

        flush(queue, api, display)

        if now >= next_poll:
            next_poll = now + 60
            try:
                state = api.get_state()
                apply_state(display, state)
                next_poll = now + max(5, int(state.get("pollSeconds", 60)))
            except (ConnectionError, ApiError) as exc:
                log.warning("état indisponible : %s", exc)

        time.sleep(1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run(Config.load())
    except KeyboardInterrupt:
        log.info("arrêt")


if __name__ == "__main__":
    main()
