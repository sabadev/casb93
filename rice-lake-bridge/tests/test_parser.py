import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bridge.parser import _parse_number, parse_ticket, strip_escp, ticket_uid


def test_strip_escp_quita_comandos_y_conserva_texto():
    raw = b"\x1b@\x1bEBASCULA\x1bF\x0f\r\nNETO 10 kg\x0c"
    assert strip_escp(raw) == "BASCULA\nNETO 10 kg\n"


def test_strip_escp_consume_parametro_de_comandos_con_argumento():
    # ESC J n avanza n/216"; la 'n' no debe aparecer como texto
    assert strip_escp(b"A\x1bJ\x18B") == "AB"


def test_parse_number_maneja_ambos_separadores_decimales():
    assert _parse_number("1.234,50") == 1234.5
    assert _parse_number("1,234.50") == 1234.5
    assert _parse_number("12345") == 12345.0
    assert _parse_number("-12.5") == -12.5
    assert _parse_number("no") is None


def test_ticket_completo_en_espanol():
    raw = (
        b"\x1b@   BASCULA CAMIONERA\r\n"
        b"Ticket No: A-00123\r\nPlaca: ABC-123\r\n"
        b"Fecha: 12/03/2026 14:35:07\r\n"
        b"BRUTO 32.450 kg\r\nTARA  12.300 kg\r\nNETO  20.150 kg\r\n\x0c"
    )
    t = parse_ticket(raw)
    assert (t.gross.value, t.tare.value, t.net.value) == (32.450, 12.300, 20.150)
    assert t.unit == "kg"
    assert t.ticket_number == "A-00123"
    assert t.vehicle_id == "ABC-123"
    assert t.printed_at.startswith("2026-03-12T14:35:07")


def test_ticket_en_ingles_formato_por_defecto_rice_lake():
    raw = b"GROSS     45280 lb\r\nTARE      15100 lb\r\nNET       30180 lb\r\n"
    t = parse_ticket(raw)
    assert t.gross.value == 45280
    assert t.net.value == 30180
    assert t.unit == "lb"


def test_neto_se_deriva_si_el_formato_no_lo_imprime():
    t = parse_ticket(b"BRUTO 100.0 kg\r\nTARA 40.5 kg\r\n")
    assert t.net.value == 59.5
    assert t.net.unit == "kg"


def test_palabra_camionera_no_se_confunde_con_etiqueta_camion():
    t = parse_ticket(b"BASCULA CAMIONERA SABA\r\nNETO 10 kg\r\n")
    assert t.vehicle_id is None


def test_orden_de_fecha_configurable():
    raw = b"Fecha: 03/04/2026 10:00\r\nNETO 1 kg\r\n"
    assert parse_ticket(raw, date_order="dmy").printed_at.startswith("2026-04-03")
    assert parse_ticket(raw, date_order="mdy").printed_at.startswith("2026-03-04")


def test_uid_es_estable_para_el_mismo_ticket():
    raw = b"NETO 10 kg\r\n"
    assert ticket_uid(raw, "2026-01-01T00:00:00Z") == ticket_uid(raw, "2026-01-01T00:00:00Z")
    assert ticket_uid(raw, "2026-01-01T00:00:00Z") != ticket_uid(b"NETO 11 kg\r\n", "2026-01-01T00:00:00Z")


def test_ticket_sin_pesos_no_revienta():
    t = parse_ticket(b"*** BASCULA FUERA DE SERVICIO ***\r\n")
    assert t.gross is None and t.net is None
    assert "FUERA DE SERVICIO" in t.text


def test_texto_con_tildes_se_parsea():
    t = parse_ticket("Camión: XY-9\r\nNETO 5 kg\r\n".encode("cp437"))
    assert t.vehicle_id == "XY-9"
