"""Loop principal del puente bascula -> backend."""

from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import serial

from .config import Config
from .framing import TicketAssembler
from .parser import parse_ticket
from .serial_link import open_printer, open_scale, open_with_retry
from .store import Spool
from .uploader import Uploader

log = logging.getLogger(__name__)

FLUSH_EVERY_S = 5.0


class Bridge:
    def __init__(self, cfg: Config, uploader: Uploader | None = None) -> None:
        self.cfg = cfg
        self.assembler = TicketAssembler(
            idle_gap_s=cfg.idle_gap_s,
            max_ticket_bytes=cfg.max_ticket_bytes,
            min_ticket_bytes=cfg.min_ticket_bytes,
        )
        self.spool = Spool(cfg.spool_db)
        self.uploader = uploader or Uploader(
            cfg.backend_url, cfg.api_token, cfg.http_timeout_s, cfg.max_retries
        )
        self._running = True

    def stop(self, *_: object) -> None:
        log.info("señal de parada recibida, cerrando...")
        self._running = False

    # ------------------------------------------------------------------ ticket
    def handle_ticket(self, raw: bytes) -> None:
        ticket = parse_ticket(raw, date_order=self.cfg.date_order)
        self._archive_raw(ticket.uid, raw)

        payload = ticket.as_dict()
        payload["scale_id"] = self.cfg.scale_id
        if self.spool.enqueue(ticket.uid, payload, ticket.captured_at):
            log.info(
                "ticket %s capturado (%d bytes) neto=%s %s",
                ticket.uid, len(raw),
                ticket.net.value if ticket.net else "?", ticket.unit or "",
            )
        else:
            log.info("ticket %s duplicado, ya estaba en la cola", ticket.uid)

    def _archive_raw(self, uid: str, raw: bytes) -> None:
        """Copia cruda en disco: la prueba de lo que realmente mando el indicador."""
        if not self.cfg.raw_dir:
            return
        try:
            day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            folder = Path(self.cfg.raw_dir) / day
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{uid}.bin").write_bytes(raw)
        except OSError as exc:
            log.warning("no se pudo archivar el ticket crudo %s: %s", uid, exc)

    # -------------------------------------------------------------------- loop
    def run(self) -> None:
        # los handlers solo pueden instalarse desde el hilo principal
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, self.stop)
            signal.signal(signal.SIGINT, self.stop)

        mode = "en linea (passthrough)" if self.cfg.printer_port else "tap pasivo"
        log.info("puente iniciado en modo %s", mode)
        log.info("cola: %s", self.spool.counts() or "vacia")

        scale = open_with_retry(open_scale, self.cfg, "puerto de la bascula")
        printer = open_with_retry(open_printer, self.cfg, "puerto de la impresora")
        last_flush = 0.0

        try:
            while self._running:
                now = time.monotonic()
                try:
                    chunk = scale.read(4096)
                except (serial.SerialException, OSError) as exc:
                    log.error("lectura fallida: %s, reabriendo puerto", exc)
                    _safe_close(scale)
                    scale = open_with_retry(open_scale, self.cfg, "puerto de la bascula")
                    continue

                if chunk:
                    # La impresion manda: primero el papel, despues el backend.
                    printer = self._passthrough(printer, chunk)
                    for raw in self.assembler.feed(chunk, now):
                        self.handle_ticket(raw)

                raw = self.assembler.tick(now)
                if raw:
                    self.handle_ticket(raw)

                if now - last_flush >= FLUSH_EVERY_S:
                    last_flush = now
                    self.uploader.flush(self.spool)

                if not chunk:
                    time.sleep(0.05)
        finally:
            # un ticket a medio recibir al momento de parar no se tira
            pending = self.assembler.tick(time.monotonic() + self.cfg.idle_gap_s + 1)
            if pending:
                self.handle_ticket(pending)
            self.uploader.flush(self.spool)
            counts = self.spool_counts_safe()
            _safe_close(scale)
            _safe_close(printer)
            self.uploader.close()
            self.spool.close()
            log.info("puente detenido. cola: %s", counts or "vacia")

    def _passthrough(self, printer, chunk: bytes):
        """Reenvia los bytes a la Epson en modo en linea."""
        if printer is None:
            return None
        try:
            printer.write(chunk)
            printer.flush()
        except (serial.SerialException, OSError) as exc:
            log.error("escritura a la impresora fallida: %s, reabriendo", exc)
            _safe_close(printer)
            return open_with_retry(open_printer, self.cfg, "puerto de la impresora")
        return printer

    def spool_counts_safe(self) -> dict[str, int]:
        try:
            return self.spool.counts()
        except Exception:  # noqa: BLE001 - solo es info de cierre
            return {}


def _safe_close(port) -> None:
    if port is None:
        return
    try:
        port.close()
    except Exception:  # noqa: BLE001
        pass
