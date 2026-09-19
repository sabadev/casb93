"""Parseo de tickets impresos por el indicador Rice Lake 480 Legend.

El indicador envia el ticket como texto plano mezclado con codigos de control
ESC/P que la Epson matricial interpreta (ESC @, ESC E, avances de pagina...).
Para forwardear a la impresora se usan los bytes crudos; para el backend se
trabaja sobre el texto ya limpio de esos codigos.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ESC/P: ESC seguido de 1 byte de comando y, segun el comando, N parametros.
# Cubrimos los comandos que el 480 emite en sus formatos de impresion.
_ESC_NO_ARG = set(b"@014568<=>EFGHIMPTqstx")  # ESC @ , ESC E, ESC F, ...
_ESC_ONE_ARG = set(b"JjSRUWwkpramglQNChfdi")  # ESC J n, ESC R n, ...

_CONTROL_KEEP = {0x09, 0x0A, 0x0D, 0x0C}  # TAB, LF, CR, FF


def strip_escp(raw: bytes) -> str:
    """Quita codigos ESC/P y devuelve el texto legible del ticket."""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        b = raw[i]
        if b == 0x1B:  # ESC
            if i + 1 >= n:
                break
            cmd = raw[i + 1]
            if cmd in _ESC_ONE_ARG:
                i += 3
            elif cmd in _ESC_NO_ARG:
                i += 2
            else:
                i += 2
            continue
        if b == 0x0F or b == 0x12 or b == 0x0E or b == 0x14:  # condensada/ancha
            i += 1
            continue
        if b < 0x20 and b not in _CONTROL_KEEP:
            i += 1
            continue
        out.append(b)
        i += 1
    text = out.decode("cp437", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")


def _deaccent(s: str) -> str:
    """Quita tildes conservando mayusculas (para regex case-insensitive)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalize(s: str) -> str:
    """minusculas sin acentos, para matchear etiquetas en ES o EN."""
    return _deaccent(s).lower()


_UNITS = r"(?:kg|lb|lbs|t|tn|g)"
# Etiqueta + numero + unidad opcional. Acepta 1.234,5 / 1,234.5 / 12345
_NUM = r"([+-]?\d[\d.,\s]*\d|\d)"

_FIELD_PATTERNS: dict[str, list[str]] = {
    "gross": [r"\b(?:gross|bruto|brutto)\b"],
    "tare": [r"\b(?:tare|tara)\b"],
    "net": [r"\b(?:net|neto)\b"],
}


def _parse_number(token: str) -> float | None:
    """Convierte '1.234,50' / '1,234.50' / '12 345' a float."""
    t = token.replace(" ", "")
    if not t:
        return None
    last_dot = t.rfind(".")
    last_comma = t.rfind(",")
    if last_dot >= 0 and last_comma >= 0:
        # el separador decimal es el que aparece mas a la derecha
        if last_comma > last_dot:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif last_comma >= 0:
        # una sola coma: decimal si deja 1-2 digitos a la derecha, si no miles
        if len(t) - last_comma - 1 in (1, 2):
            t = t.replace(",", ".")
        else:
            t = t.replace(",", "")
    elif last_dot >= 0 and len(t) - last_dot - 1 == 3 and t.count(".") >= 1:
        # 1.234 -> ambiguo; el 480 imprime decimales, se respeta como decimal
        pass
    try:
        return float(t)
    except ValueError:
        return None


@dataclass(slots=True)
class Weight:
    value: float
    unit: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.value, "unit": self.unit}


@dataclass(slots=True)
class Ticket:
    """Ticket normalizado listo para enviar al backend."""

    uid: str
    captured_at: str
    raw_b64: str
    text: str
    lines: list[str]
    gross: Weight | None = None
    tare: Weight | None = None
    net: Weight | None = None
    unit: str | None = None
    ticket_number: str | None = None
    vehicle_id: str | None = None
    printed_at: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "uid": self.uid,
            "captured_at": self.captured_at,
            "printed_at": self.printed_at,
            "unit": self.unit,
            "gross": self.gross.as_dict() if self.gross else None,
            "tare": self.tare.as_dict() if self.tare else None,
            "net": self.net.as_dict() if self.net else None,
            "ticket_number": self.ticket_number,
            "vehicle_id": self.vehicle_id,
            "extra": self.extra,
            "text": self.text,
            "raw_b64": self.raw_b64,
            "lines": self.lines,
        }


_UNIT_RE = re.compile(rf"\b({_UNITS})\b", re.IGNORECASE)
_TICKET_NO_RE = re.compile(
    r"\b(?:ticket|tiquete|boleta|folio|consecutivo|comprobante)\b\.?"
    r"(?:\s*(?:no|nro|num|number|#)\b\.?)?"
    r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{0,19})",
    re.IGNORECASE,
)
_VEHICLE_RE = re.compile(
    r"\b(?:placa|patente|vehiculo|veh|truck|camion|unidad|tag|id)\b\.?"
    r"\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{2,15})\b",
    re.IGNORECASE,
)
_DATETIME_RE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
    r"(?:[\s,]+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp]\.?[Mm]\.?)?))?"
)
_KV_RE = re.compile(r"^\s*([A-Za-z][A-Za-z .\-/]{1,24}?)\s*[:=]\s*(.+?)\s*$")


def _find_weight(norm_line: str, raw_line: str, patterns: list[str]) -> Weight | None:
    for pat in patterns:
        m = re.search(pat, norm_line)
        if not m:
            continue
        tail = raw_line[m.end():]
        num_m = re.search(_NUM, tail)
        if not num_m:
            continue
        value = _parse_number(num_m.group(1))
        if value is None:
            continue
        unit_m = _UNIT_RE.search(tail[num_m.end():])
        unit = unit_m.group(1).lower() if unit_m else None
        return Weight(value=value, unit=unit)
    return None


def _parse_printed_at(text: str, date_order: str = "dmy") -> str | None:
    m = _DATETIME_RE.search(text)
    if not m:
        return None
    date_s, time_s = m.group(1), m.group(2) or "00:00:00"
    time_s = time_s.strip().upper().replace(".", "")
    sep = "/" if "/" in date_s else "-"
    parts = date_s.split(sep)
    y = "%Y" if len(parts[2]) == 4 else "%y"
    dmy, mdy = f"%d{sep}%m{sep}{y}", f"%m{sep}%d{sep}{y}"
    fmts = [dmy, mdy] if date_order == "dmy" else [mdy, dmy]
    for tf in ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p"):
        for df in fmts:
            try:
                return datetime.strptime(f"{date_s} {time_s}", f"{df} {tf}").isoformat()
            except ValueError:
                continue
    return None


def ticket_uid(raw: bytes, captured_at: str) -> str:
    """Identificador estable: mismo ticket reenviado => mismo uid (idempotencia)."""
    h = hashlib.sha256()
    h.update(raw)
    h.update(captured_at.encode())
    return h.hexdigest()[:32]


def parse_ticket(
    raw: bytes,
    captured_at: datetime | None = None,
    date_order: str = "dmy",
) -> Ticket:
    """Convierte los bytes crudos de un ticket en un objeto Ticket."""
    import base64

    when = (captured_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    captured_iso = when.isoformat()
    text = strip_escp(raw)
    lines = [ln.rstrip() for ln in text.split("\n")]
    non_empty = [ln for ln in lines if ln.strip()]

    ticket = Ticket(
        uid=ticket_uid(raw, captured_iso),
        captured_at=captured_iso,
        raw_b64=base64.b64encode(raw).decode("ascii"),
        text="\n".join(non_empty),
        lines=non_empty,
    )

    for raw_line in non_empty:
        norm = _normalize(raw_line)
        for field_name, patterns in _FIELD_PATTERNS.items():
            if getattr(ticket, field_name) is None:
                w = _find_weight(norm, raw_line, patterns)
                if w:
                    setattr(ticket, field_name, w)

    # unidad del ticket: la primera declarada en cualquier peso
    for w in (ticket.gross, ticket.net, ticket.tare):
        if w and w.unit:
            ticket.unit = w.unit
            break
    if ticket.unit is None:
        m = _UNIT_RE.search(ticket.text)
        ticket.unit = m.group(1).lower() if m else None

    # neto derivado cuando el formato no lo imprime
    if ticket.net is None and ticket.gross and ticket.tare:
        ticket.net = Weight(
            value=round(ticket.gross.value - ticket.tare.value, 4), unit=ticket.unit
        )

    searchable = _deaccent(ticket.text)
    m = _TICKET_NO_RE.search(searchable)
    if m:
        ticket.ticket_number = m.group(1).strip()
    m = _VEHICLE_RE.search(searchable)
    if m:
        ticket.vehicle_id = m.group(1).strip().upper()
    ticket.printed_at = _parse_printed_at(searchable, date_order)

    # cualquier "Etiqueta: valor" adicional queda disponible en extra
    for raw_line in non_empty:
        kv = _KV_RE.match(raw_line)
        if kv:
            key = _normalize(kv.group(1)).strip().replace(" ", "_")
            if key and key not in ticket.extra:
                ticket.extra[key] = kv.group(2)
    return ticket
