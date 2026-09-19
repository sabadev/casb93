"""Envio de tickets al backend con reintentos e idempotencia."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from .store import Spool, backoff_seconds

log = logging.getLogger(__name__)


class Uploader:
    """Vacia la cola contra el backend.

    Idempotencia: el uid del ticket viaja en la cabecera `Idempotency-Key`,
    asi un reintento tras un timeout no duplica el pesaje en el backend.
    """

    def __init__(
        self,
        url: str,
        token: str | None = None,
        timeout_s: float = 10.0,
        max_retries: int = 8,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self.max_retries = max_retries
        self._client = client or httpx.Client(timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    def _headers(self, uid: str) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Idempotency-Key": uid}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def send(self, uid: str, payload: dict[str, Any]) -> tuple[bool, str]:
        """Devuelve (ok, detalle). ok=False => reintentar segun backoff."""
        try:
            resp = self._client.post(
                self.url, content=json.dumps(payload).encode(), headers=self._headers(uid)
            )
        except httpx.HTTPError as exc:
            return False, f"{type(exc).__name__}: {exc}"

        if 200 <= resp.status_code < 300:
            return True, f"HTTP {resp.status_code}"
        # 4xx (salvo 408/429) es un payload que el backend nunca va a aceptar:
        # reintentarlo solo gasta la cola, se marca para revision manual.
        permanent = 400 <= resp.status_code < 500 and resp.status_code not in (408, 429)
        detail = f"HTTP {resp.status_code}: {resp.text[:200]}"
        return False, ("PERMANENT " + detail) if permanent else detail

    def flush(self, spool: Spool, limit: int = 20) -> tuple[int, int]:
        """Intenta enviar los tickets vencidos. Devuelve (enviados, fallidos)."""
        sent = failed = 0
        for row in spool.due(limit=limit):
            uid = row["uid"]
            payload = json.loads(row["payload"])
            ok, detail = self.send(uid, payload)
            if ok:
                spool.mark_sent(uid)
                sent += 1
                log.info("ticket %s enviado (%s)", uid, detail)
                continue

            failed += 1
            attempts = row["attempts"] + 1
            if detail.startswith("PERMANENT") or attempts >= self.max_retries:
                spool.mark_dead(uid, detail)
                log.error("ticket %s descartado tras %d intentos: %s", uid, attempts, detail)
            else:
                delay = backoff_seconds(row["attempts"])
                spool.mark_failed(uid, detail, delay)
                log.warning(
                    "ticket %s fallo (intento %d), reintento en %.0fs: %s",
                    uid, attempts, delay, detail,
                )
        return sent, failed
