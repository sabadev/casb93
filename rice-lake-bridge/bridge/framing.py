"""Ensamblado de tickets a partir del flujo de bytes del indicador.

El 480 no delimita el ticket: manda las lineas y se calla. Un ticket se cierra
cuando ocurre lo primero de:
  - llega un form feed (0x0C), que la Epson usa para expulsar la hoja;
  - pasan `idle_gap_s` segundos sin recibir un solo byte;
  - se supera `max_ticket_bytes` (proteccion ante un puerto que no calla).
"""

from __future__ import annotations

from dataclasses import dataclass, field

FORM_FEED = 0x0C


@dataclass(slots=True)
class TicketAssembler:
    idle_gap_s: float = 1.2
    max_ticket_bytes: int = 65536
    min_ticket_bytes: int = 8

    _buf: bytearray = field(default_factory=bytearray)
    _last_byte_at: float | None = None

    @property
    def pending_bytes(self) -> int:
        return len(self._buf)

    def feed(self, chunk: bytes, now: float) -> list[bytes]:
        """Agrega bytes recibidos. Devuelve los tickets cerrados por este chunk."""
        tickets: list[bytes] = []
        if not chunk:
            return tickets
        for byte in chunk:
            self._buf.append(byte)
            if byte == FORM_FEED or len(self._buf) >= self.max_ticket_bytes:
                done = self._close()
                if done is not None:
                    tickets.append(done)
        self._last_byte_at = now
        return tickets

    def tick(self, now: float) -> bytes | None:
        """Cierra el ticket si ya paso el silencio configurado. Llamar en el loop."""
        if not self._buf or self._last_byte_at is None:
            return None
        if now - self._last_byte_at < self.idle_gap_s:
            return None
        return self._close()

    def _close(self) -> bytes | None:
        raw = bytes(self._buf)
        self._buf.clear()
        self._last_byte_at = None
        # ruido de linea o un form feed suelto no son un ticket
        if len(raw.strip(b"\x00\x0c\r\n ")) < self.min_ticket_bytes:
            return None
        return raw
