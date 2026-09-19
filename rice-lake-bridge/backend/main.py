"""Backend receptor de pesajes (FastAPI).

Es una referencia funcional y minima: recibe el ticket, lo valida, lo guarda de
forma idempotente y lo expone para consulta. Si ya tienes un backend, lo unico
que debes replicar es el contrato de /api/weighings descrito en el README.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

DB_PATH = Path(os.environ.get("BACKEND_DB", "weighings.db"))
API_TOKEN = os.environ.get("API_TOKEN")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS weighings (
    uid            TEXT PRIMARY KEY,
    scale_id       TEXT NOT NULL,
    captured_at    TEXT NOT NULL,
    printed_at     TEXT,
    unit           TEXT,
    gross          REAL,
    tare           REAL,
    net            REAL,
    ticket_number  TEXT,
    vehicle_id     TEXT,
    text           TEXT,
    raw_b64        TEXT,
    extra          TEXT,
    received_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_weighings_scale ON weighings (scale_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_weighings_vehicle ON weighings (vehicle_id);
"""


def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(str(DB_PATH), isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = get_db()
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(_SCHEMA)
    db.close()
    yield


app = FastAPI(title="Pesajes bascula camionera", version="1.0.0", lifespan=lifespan)


class WeightIn(BaseModel):
    value: float
    unit: str | None = None


class WeighingIn(BaseModel):
    uid: str = Field(min_length=8, max_length=64)
    scale_id: str
    captured_at: str
    printed_at: str | None = None
    unit: str | None = None
    gross: WeightIn | None = None
    tare: WeightIn | None = None
    net: WeightIn | None = None
    ticket_number: str | None = None
    vehicle_id: str | None = None
    text: str | None = None
    raw_b64: str | None = None
    lines: list[str] | None = None
    extra: dict[str, str] = Field(default_factory=dict)


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not API_TOKEN:  # sin token configurado el endpoint queda abierto (solo dev)
        return
    if authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token invalido")


@app.get("/health")
def health() -> dict[str, Any]:
    db = get_db()
    try:
        total = db.execute("SELECT COUNT(*) c FROM weighings").fetchone()["c"]
    finally:
        db.close()
    return {"status": "ok", "weighings": total}


@app.post("/api/weighings", status_code=status.HTTP_201_CREATED)
def create_weighing(
    body: WeighingIn,
    response: Response,
    _: Annotated[None, Depends(require_token)] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if idempotency_key and idempotency_key != body.uid:
        raise HTTPException(400, "Idempotency-Key no coincide con uid")

    db = get_db()
    try:
        existing = db.execute(
            "SELECT uid FROM weighings WHERE uid=?", (body.uid,)
        ).fetchone()
        if existing:
            # Reintento del puente tras un timeout: no se duplica el pesaje.
            response.status_code = status.HTTP_200_OK
            return {"uid": body.uid, "duplicate": True}

        db.execute(
            "INSERT INTO weighings (uid, scale_id, captured_at, printed_at, unit,"
            " gross, tare, net, ticket_number, vehicle_id, text, raw_b64, extra,"
            " received_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                body.uid, body.scale_id, body.captured_at, body.printed_at, body.unit,
                body.gross.value if body.gross else None,
                body.tare.value if body.tare else None,
                body.net.value if body.net else None,
                body.ticket_number, body.vehicle_id, body.text, body.raw_b64,
                json.dumps(body.extra, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    finally:
        db.close()
    return {"uid": body.uid, "duplicate": False}


@app.get("/api/weighings")
def list_weighings(
    _: Annotated[None, Depends(require_token)] = None,
    scale_id: str | None = None,
    vehicle_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    sql = ("SELECT uid, scale_id, captured_at, printed_at, unit, gross, tare, net,"
           " ticket_number, vehicle_id, received_at FROM weighings WHERE 1=1")
    params: list[Any] = []
    if scale_id:
        sql += " AND scale_id=?"
        params.append(scale_id)
    if vehicle_id:
        sql += " AND vehicle_id=?"
        params.append(vehicle_id.upper())
    sql += " ORDER BY captured_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]

    db = get_db()
    try:
        rows = [dict(r) for r in db.execute(sql, params)]
    finally:
        db.close()
    return {"count": len(rows), "items": rows}


@app.get("/api/weighings/{uid}")
def get_weighing(uid: str, _: Annotated[None, Depends(require_token)] = None) -> dict[str, Any]:
    db = get_db()
    try:
        row = db.execute("SELECT * FROM weighings WHERE uid=?", (uid,)).fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(404, "pesaje no encontrado")
    item = dict(row)
    item["extra"] = json.loads(item["extra"] or "{}")
    return item
