"""Acceso al puerto serie con reconexion automatica.

Si se desconecta el USB-RS232 o el indicador se apaga, el servicio no muere:
reintenta abrir el puerto hasta que vuelva.
"""

from __future__ import annotations

import logging
import time

import serial

from .config import Config

log = logging.getLogger(__name__)

_PARITY = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
_STOPBITS = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}
_BYTESIZE = {7: serial.SEVENBITS, 8: serial.EIGHTBITS}


def open_scale(cfg: Config) -> serial.Serial:
    """Abre el puerto del indicador. Solo lectura logica: nunca le escribimos."""
    return serial.Serial(
        port=cfg.scale_port,
        baudrate=cfg.baudrate,
        bytesize=_BYTESIZE.get(cfg.bytesize, serial.EIGHTBITS),
        parity=_PARITY.get(cfg.parity, serial.PARITY_NONE),
        stopbits=_STOPBITS.get(cfg.stopbits, serial.STOPBITS_ONE),
        rtscts=cfg.rtscts,
        xonxoff=cfg.xonxoff,
        timeout=0.2,
    )


def open_printer(cfg: Config) -> serial.Serial | None:
    """Abre el puerto hacia la Epson (solo en modo en linea)."""
    if not cfg.printer_port:
        return None
    return serial.Serial(
        port=cfg.printer_port,
        baudrate=cfg.printer_baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        rtscts=cfg.rtscts,
        xonxoff=cfg.xonxoff,
        timeout=1.0,
        write_timeout=5.0,
    )


def open_with_retry(opener, cfg: Config, what: str, max_wait: float = 30.0):
    """Abre un puerto reintentando con backoff hasta lograrlo."""
    delay = 1.0
    while True:
        try:
            port = opener(cfg)
            if port is not None:
                log.info("%s abierto: %s", what, port.port)
            return port
        except (serial.SerialException, OSError) as exc:
            log.error("no se pudo abrir %s: %s (reintento en %.0fs)", what, exc, delay)
            time.sleep(delay)
            delay = min(max_wait, delay * 2)
