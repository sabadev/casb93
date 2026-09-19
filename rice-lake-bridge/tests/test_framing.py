import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.framing import TicketAssembler


def test_cierra_por_form_feed():
    a = TicketAssembler()
    assert a.feed(b"NETO 10 kg\r\n\x0c", now=0.0) == [b"NETO 10 kg\r\n\x0c"]


def test_cierra_por_silencio():
    a = TicketAssembler(idle_gap_s=1.0)
    assert a.feed(b"NETO 10 kg\r\n", now=0.0) == []
    assert a.tick(now=0.9) is None
    assert a.tick(now=1.1) == b"NETO 10 kg\r\n"
    assert a.tick(now=5.0) is None  # ya consumido


def test_ticket_partido_en_varios_chunks_se_une():
    a = TicketAssembler(idle_gap_s=1.0)
    a.feed(b"BRUTO 100 kg\r\n", now=0.0)
    a.feed(b"TARA 40 kg\r\n", now=0.3)
    assert a.tick(now=1.4) == b"BRUTO 100 kg\r\nTARA 40 kg\r\n"


def test_ruido_de_linea_no_genera_ticket():
    a = TicketAssembler(idle_gap_s=1.0, min_ticket_bytes=8)
    a.feed(b"\x00\r\n", now=0.0)
    assert a.tick(now=2.0) is None


def test_corta_si_supera_el_maximo():
    a = TicketAssembler(max_ticket_bytes=16)
    out = a.feed(b"A" * 40, now=0.0)
    assert len(out) == 2 and all(len(t) == 16 for t in out)
    assert a.pending_bytes == 8
