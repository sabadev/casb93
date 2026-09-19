"""End-to-end sobre un puerto serie virtual (pty): indicador -> puente -> backend."""

import json
import os
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.config import Config
from bridge.service import Bridge
from bridge.store import Spool
from bridge.uploader import Uploader

TICKET = (
    b"\x1b@\x1bE   BASCULA CAMIONERA SABA\x1bF\r\n"
    b"Ticket No: A-00777\r\nPlaca: TKM-884\r\n"
    b"Fecha: 12/03/2026 09:12:00\r\n"
    b"BRUTO 32.450 kg\r\nTARA  12.300 kg\r\nNETO  20.150 kg\r\n\x0c"
)


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="requiere pty (Unix)")
def test_ticket_impreso_llega_al_backend(tmp_path):
    master, slave = os.openpty()
    recibidos = []

    def backend(request: httpx.Request) -> httpx.Response:
        recibidos.append((request.headers.get("Idempotency-Key"),
                          json.loads(request.content)))
        return httpx.Response(201, json={"ok": True})

    cfg = Config(
        scale_port=os.ttyname(slave),
        idle_gap_s=0.3,
        spool_db=str(tmp_path / "spool.db"),
        raw_dir=str(tmp_path / "raw"),
        scale_id="bascula-test",
    )
    uploader = Uploader(
        "http://backend/api/weighings",
        client=httpx.Client(transport=httpx.MockTransport(backend)),
    )
    bridge = Bridge(cfg, uploader=uploader)

    hilo = threading.Thread(target=bridge.run, daemon=True)
    hilo.start()
    time.sleep(0.5)                      # deja que abra el puerto

    os.write(master, TICKET)             # el indicador "imprime"
    deadline = time.time() + 10
    while not recibidos and time.time() < deadline:
        time.sleep(0.1)

    bridge.stop()
    hilo.join(timeout=10)
    os.close(master)
    os.close(slave)

    assert len(recibidos) == 1, "el ticket debio enviarse exactamente una vez"
    uid, payload = recibidos[0]
    assert uid == payload["uid"]                       # idempotencia
    assert payload["scale_id"] == "bascula-test"
    assert payload["net"]["value"] == 20.150
    assert payload["gross"]["value"] == 32.450
    assert payload["vehicle_id"] == "TKM-884"
    assert payload["ticket_number"] == "A-00777"

    # el ticket quedo marcado como enviado y archivado en crudo
    with Spool(cfg.spool_db) as spool:
        assert spool.counts() == {"sent": 1}
    archivados = list(Path(cfg.raw_dir).rglob("*.bin"))
    assert len(archivados) == 1
    assert archivados[0].read_bytes() == TICKET


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="requiere pty (Unix)")
def test_backend_caido_no_pierde_el_pesaje(tmp_path):
    """Con el backend inalcanzable el ticket queda en cola, no se pierde."""
    master, slave = os.openpty()

    def backend(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    cfg = Config(
        scale_port=os.ttyname(slave), idle_gap_s=0.3,
        spool_db=str(tmp_path / "spool.db"), raw_dir=None,
    )
    bridge = Bridge(cfg, uploader=Uploader(
        "http://backend/api/weighings",
        client=httpx.Client(transport=httpx.MockTransport(backend)),
    ))
    hilo = threading.Thread(target=bridge.run, daemon=True)
    hilo.start()
    time.sleep(0.5)
    os.write(master, TICKET)
    time.sleep(1.5)
    bridge.stop()
    hilo.join(timeout=10)
    os.close(master)
    os.close(slave)

    with Spool(cfg.spool_db) as spool:
        assert spool.counts() == {"pending": 1}
        fila = next(spool.iter_all("pending"))
        assert json.loads(fila["payload"])["net"]["value"] == 20.150


@pytest.mark.skipif(not hasattr(os, "openpty"), reason="requiere pty (Unix)")
def test_modo_en_linea_reenvia_los_bytes_intactos_a_la_impresora(tmp_path):
    """En passthrough la Epson debe recibir EXACTAMENTE lo que mando el indicador,
    codigos ESC/P incluidos: la impresion no puede degradarse por el puente."""
    bascula_m, bascula_s = os.openpty()
    impresora_m, impresora_s = os.openpty()

    cfg = Config(
        scale_port=os.ttyname(bascula_s),
        printer_port=os.ttyname(impresora_s),
        idle_gap_s=0.3,
        spool_db=str(tmp_path / "spool.db"),
        raw_dir=None,
    )
    bridge = Bridge(cfg, uploader=Uploader(
        "http://backend/api/weighings",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(201, json={}))
        ),
    ))
    hilo = threading.Thread(target=bridge.run, daemon=True)
    hilo.start()
    time.sleep(0.5)

    os.write(bascula_m, TICKET)
    impreso = b""
    deadline = time.time() + 5
    while len(impreso) < len(TICKET) and time.time() < deadline:
        impreso += os.read(impresora_m, 4096)

    bridge.stop()
    hilo.join(timeout=10)
    for fd in (bascula_m, bascula_s, impresora_m, impresora_s):
        os.close(fd)

    assert impreso == TICKET
