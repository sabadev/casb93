"""CLI del puente Rice Lake 480 -> backend.

  python -m bridge.main run              servicio en vivo
  python -m bridge.main ports            lista los puertos serie detectados
  python -m bridge.main sniff            vuelca en pantalla lo que llega (diagnostico)
  python -m bridge.main replay ticket.bin   reprocesa un ticket crudo archivado
  python -m bridge.main status           estado de la cola local
  python -m bridge.main retry            reencola los tickets marcados 'dead'
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from .config import Config, load_dotenv
from .parser import parse_ticket
from .service import Bridge
from .store import Spool


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def cmd_run(cfg: Config, _args: argparse.Namespace) -> int:
    Bridge(cfg).run()
    return 0


def cmd_ports(_cfg: Config, _args: argparse.Namespace) -> int:
    from serial.tools import list_ports

    found = list(list_ports.comports())
    if not found:
        print("No se detectaron puertos serie.")
        print("Con un adaptador USB-RS232 revisa: dmesg | tail  y  ls -l /dev/ttyUSB*")
        return 1
    for p in found:
        print(f"{p.device:20} {p.description} [{p.hwid}]")
    return 0


def cmd_sniff(cfg: Config, args: argparse.Namespace) -> int:
    """Muestra lo que manda el indicador. Sirve para confirmar baudios y formato."""
    import serial

    from .serial_link import open_scale

    print(
        f"Escuchando {cfg.scale_port} a {cfg.baudrate} "
        f"{cfg.bytesize}{cfg.parity}{cfg.stopbits}. Presiona PRINT en el indicador."
    )
    print("Ctrl+C para salir.\n")
    try:
        port = open_scale(cfg)
    except (serial.SerialException, OSError) as exc:
        print(f"ERROR abriendo {cfg.scale_port}: {exc}", file=sys.stderr)
        return 1

    captured = bytearray()
    try:
        while True:
            chunk = port.read(4096)
            if not chunk:
                continue
            captured += chunk
            sys.stdout.write(chunk.decode("cp437", errors="replace"))
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\n\n--- resumen ---")
        print(f"{len(captured)} bytes recibidos")
        if captured:
            print("hex:", captured[:200].hex(" "))
            if args.save:
                Path(args.save).write_bytes(bytes(captured))
                print(f"guardado en {args.save}")
            print("\nparseo resultante:")
            d = parse_ticket(bytes(captured), date_order=cfg.date_order).as_dict()
            d.pop("raw_b64", None)
            print(json.dumps(d, indent=2, ensure_ascii=False))
    finally:
        port.close()
    return 0


def cmd_replay(cfg: Config, args: argparse.Namespace) -> int:
    raw = Path(args.file).read_bytes()
    ticket = parse_ticket(raw, date_order=cfg.date_order)
    payload = ticket.as_dict()
    payload["scale_id"] = cfg.scale_id
    if args.send:
        from .uploader import Uploader

        up = Uploader(cfg.backend_url, cfg.api_token, cfg.http_timeout_s)
        ok, detail = up.send(ticket.uid, payload)
        up.close()
        print(f"{'OK' if ok else 'FALLO'}: {detail}")
        return 0 if ok else 1
    payload.pop("raw_b64", None)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_status(cfg: Config, _args: argparse.Namespace) -> int:
    with Spool(cfg.spool_db) as spool:
        counts = spool.counts()
        print(f"Cola: {cfg.spool_db}")
        print(f"  pendientes : {counts.get('pending', 0)}")
        print(f"  enviados   : {counts.get('sent', 0)}")
        print(f"  descartados: {counts.get('dead', 0)}")
        dead = list(spool.iter_all("dead"))
        if dead:
            print("\nDescartados (revisar):")
            for row in dead[:20]:
                print(f"  {row['uid']}  {row['captured_at']}  {row['last_error']}")
    return 0


def cmd_retry(cfg: Config, _args: argparse.Namespace) -> int:
    with Spool(cfg.spool_db) as spool:
        cur = spool._db.execute(
            "UPDATE tickets SET status='pending', attempts=0, next_retry_at=0 "
            "WHERE status='dead'"
        )
        print(f"{cur.rowcount} ticket(s) reencolados")
        if cur.rowcount:
            from .uploader import Uploader

            up = Uploader(cfg.backend_url, cfg.api_token, cfg.http_timeout_s, cfg.max_retries)
            sent, failed = up.flush(spool, limit=1000)
            up.close()
            print(f"enviados: {sent}  fallidos: {failed}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="bridge", description=__doc__)
    ap.add_argument("--env", default=".env", help="archivo .env a cargar")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run", help="ejecuta el puente")
    sub.add_parser("ports", help="lista puertos serie")
    sniff = sub.add_parser("sniff", help="vuelca lo que llega por el puerto")
    sniff.add_argument("--save", help="guarda los bytes crudos en este archivo")
    replay = sub.add_parser("replay", help="reprocesa un ticket crudo")
    replay.add_argument("file")
    replay.add_argument("--send", action="store_true", help="ademas lo envia al backend")
    sub.add_parser("status", help="estado de la cola")
    sub.add_parser("retry", help="reencola los tickets descartados")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(args.env)
    cfg = Config.from_env()
    _setup_logging(cfg.log_level)
    handlers = {
        "run": cmd_run, "ports": cmd_ports, "sniff": cmd_sniff,
        "replay": cmd_replay, "status": cmd_status, "retry": cmd_retry,
    }
    return handlers[args.cmd](cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
