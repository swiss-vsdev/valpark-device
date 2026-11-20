"""Client HTTP pour l'API du boîtier (contrat device-api.md)."""
from __future__ import annotations

import requests


class ApiError(Exception):
    pass


class BadRequest(ApiError):
    """400 : ne jamais renvoyer ce lot tel quel."""


class Unauthorized(ApiError):
    pass


class RateLimited(ApiError):
    pass


class ApiClient:
    def __init__(self, base: str, token: str, timeout: int = 15):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def _request(self, method: str, path: str, payload: object = None) -> dict:
        try:
            response = self.session.request(
                method, self.base + path, json=payload, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise ConnectionError(str(exc)) from exc

        if response.status_code == 401:
            raise Unauthorized("jeton absent, mal formé ou inconnu")
        if response.status_code == 429:
            raise RateLimited("plus de 60 requêtes/minute")
        if response.status_code == 400:
            raise BadRequest(response.text)
        if not response.ok:
            raise ApiError(f"{method} {path} → {response.status_code} {response.text}")
        return response.json()

    def post_events(self, events: list[dict]) -> dict:
        """202 immédiat : accepted, duplicates, display, pollSeconds."""
        return self._request("POST", "/api/device/v1/events", {"events": events})

    def get_state(self) -> dict:
        """display (version, icon, line1..3, inverted) + pollSeconds."""
        return self._request("GET", "/api/device/v1/state")
