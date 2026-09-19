"""Configuracion del puente, via variables de entorno o archivo .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    return int(raw) if raw not in (None, "") else default


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    return float(raw) if raw not in (None, "") else default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on", "si", "sí")


def load_dotenv(path: str | Path = ".env") -> None:
    """Carga un .env sencillo sin pisar variables ya definidas en el entorno."""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(slots=True)
class Config:
    # --- puerto conectado al indicador Rice Lake 480 ---
    scale_port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"          # N, E, O
    stopbits: int = 1
    rtscts: bool = False
    xonxoff: bool = False

    # --- passthrough opcional hacia la Epson matricial (modo en linea) ---
    printer_port: str | None = None   # None => modo tap pasivo
    printer_baudrate: int = 9600

    # --- framing del ticket ---
    idle_gap_s: float = 1.2      # silencio que cierra un ticket
    max_ticket_bytes: int = 65536
    min_ticket_bytes: int = 8

    # --- backend ---
    backend_url: str = "http://localhost:8000/api/weighings"
    api_token: str | None = None
    scale_id: str = "bascula-01"
    http_timeout_s: float = 10.0
    max_retries: int = 8

    # --- almacenamiento local ---
    spool_db: str = "/var/lib/rice-lake-bridge/spool.db"
    raw_dir: str | None = "/var/lib/rice-lake-bridge/raw"

    date_order: str = "dmy"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            scale_port=_env("SCALE_PORT", "/dev/ttyUSB0"),
            baudrate=_env_int("SCALE_BAUDRATE", 9600),
            bytesize=_env_int("SCALE_BYTESIZE", 8),
            parity=(_env("SCALE_PARITY", "N") or "N").upper(),
            stopbits=_env_int("SCALE_STOPBITS", 1),
            rtscts=_env_bool("SCALE_RTSCTS", False),
            xonxoff=_env_bool("SCALE_XONXOFF", False),
            printer_port=_env("PRINTER_PORT") or None,
            printer_baudrate=_env_int("PRINTER_BAUDRATE", 9600),
            idle_gap_s=_env_float("IDLE_GAP_S", 1.2),
            max_ticket_bytes=_env_int("MAX_TICKET_BYTES", 65536),
            min_ticket_bytes=_env_int("MIN_TICKET_BYTES", 8),
            backend_url=_env("BACKEND_URL", "http://localhost:8000/api/weighings"),
            api_token=_env("API_TOKEN") or None,
            scale_id=_env("SCALE_ID", "bascula-01"),
            http_timeout_s=_env_float("HTTP_TIMEOUT_S", 10.0),
            max_retries=_env_int("MAX_RETRIES", 8),
            spool_db=_env("SPOOL_DB", "/var/lib/rice-lake-bridge/spool.db"),
            raw_dir=_env("RAW_DIR", "/var/lib/rice-lake-bridge/raw") or None,
            date_order=(_env("DATE_ORDER", "dmy") or "dmy").lower(),
            log_level=(_env("LOG_LEVEL", "INFO") or "INFO").upper(),
        )
