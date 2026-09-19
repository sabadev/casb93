# Puente Rice Lake 480 Legend → backend

Captura los tickets de pesaje que el indicador **Rice Lake 480 Legend**
envía por puerto serie a la impresora Epson matricial cuando se presiona
**PRINT**, los interpreta y los publica en un backend por HTTP.

La impresión en papel sigue funcionando exactamente igual: el puente escucha
la misma línea, no la reemplaza.

```
  celdas de carga → caja suma → Rice Lake 480 ──serial──▶ Epson matricial
                                       │
                                       └──▶ puente (Raspberry Pi) ──HTTP──▶ backend
```

## Cómo funciona

1. **Escucha** el puerto serie y arma el ticket: cierra cuando llega un
   form feed (`0x0C`) o cuando el indicador se calla `IDLE_GAP_S` segundos.
2. **Interpreta** el texto quitando los códigos ESC/P de la Epson, y extrae
   bruto, tara, neto, unidad, número de ticket, placa y fecha.
3. **Encola en disco (SQLite) antes de enviar.** Si el backend o la red
   están caídos, el pesaje no se pierde: se reintenta con backoff hasta que
   entre.
4. **Envía** con cabecera `Idempotency-Key`, así un reintento tras un
   timeout nunca duplica el pesaje.

También guarda una copia cruda de cada ticket en `RAW_DIR`: es la prueba de
lo que realmente mandó el indicador, y sirve para reprocesar con `replay` si
más adelante ajustas el parser.

## Puesta en marcha

### 1. Cableado

**Lee [`docs/01-cableado.md`](docs/01-cableado.md) antes de conectar nada.**
La opción recomendada es un tap pasivo sobre la línea TX: si el Pi se cae,
la báscula sigue imprimiendo.

### 2. Instalación

```bash
git clone <este-repo> /opt/rice-lake-bridge
cd /opt/rice-lake-bridge/rice-lake-bridge
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
sudo usermod -aG dialout $USER     # acceso al puerto serie (requiere re-login)
```

### 3. Descubre los parámetros reales del puerto

```bash
.venv/bin/python -m bridge.main ports      # qué adaptadores ve el sistema
```

Copia en `.env` los valores del menú **SERIAL** del indicador (ver
[`docs/02-indicador.md`](docs/02-indicador.md)) y comprueba que llega bien:

```bash
.venv/bin/python -m bridge.main sniff --save ticket-real.bin
# presiona PRINT en el indicador; Ctrl+C para ver el resumen y el parseo
```

Si sale texto legible, los parámetros son correctos. Si sale basura, el
baudrate o la paridad no coinciden.

### 4. Arranca el servicio

```bash
sudo cp systemd/rice-lake-bridge.service /etc/systemd/system/
sudo systemctl enable --now rice-lake-bridge
journalctl -u rice-lake-bridge -f
```

## Uso diario

```bash
python -m bridge.main status              # cuántos pendientes / enviados / descartados
python -m bridge.main retry               # reintenta los descartados tras arreglar el backend
python -m bridge.main replay t.bin        # reprocesa un ticket archivado (muestra el JSON)
python -m bridge.main replay t.bin --send # y lo envía al backend
```

## Contrato con el backend

`POST {BACKEND_URL}` con `Authorization: Bearer {API_TOKEN}` y
`Idempotency-Key: {uid}`:

```json
{
  "uid": "a07258baec46ca55a784e482b59254ab",
  "scale_id": "bascula-01",
  "captured_at": "2026-03-12T14:35:07.123456+00:00",
  "printed_at": "2026-03-12T14:35:07",
  "unit": "kg",
  "gross": { "value": 32450.0, "unit": "kg" },
  "tare":  { "value": 12300.0, "unit": "kg" },
  "net":   { "value": 20150.0, "unit": "kg" },
  "ticket_number": "A-00123",
  "vehicle_id": "ABC-123",
  "extra": { "placa": "ABC-123", "fecha": "12/03/2026 14:35:07" },
  "text": "BASCULA CAMIONERA SABA\nTicket No: A-00123\n...",
  "lines": ["BASCULA CAMIONERA SABA", "Ticket No: A-00123", "..."],
  "raw_b64": "G0AbRSAgIEJBU0NVTEE..."
}
```

Respuestas que el puente espera:

| Código | Interpretación |
|---|---|
| `2xx` | recibido, se marca como enviado |
| `408`, `429`, `5xx` | temporal, reintenta con backoff (2s, 4s… hasta 10 min) |
| otro `4xx` | payload que nunca será aceptado: se marca `dead` y **no se borra** |

Campos mínimos que debe aceptar tu backend: `uid`, `scale_id`, `captured_at`
y `net`. El resto es opcional. Usa `uid` como clave única — es lo que hace
que el reintento sea seguro.

### Backend de referencia

Si aún no tienes backend, `backend/main.py` es uno funcional (FastAPI +
SQLite) que ya implementa este contrato:

```bash
API_TOKEN=xxx .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
# GET /api/weighings?vehicle_id=ABC-123
# GET /api/weighings/{uid}
# GET /health
```

Si ya tienes backend, ignora esta carpeta y replica el contrato de arriba.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

Incluye tests end-to-end sobre puertos serie virtuales (`pty`) que verifican
el camino completo indicador → puente → backend, que un backend caído no
pierde el pesaje, y que en modo passthrough la Epson recibe los bytes
idénticos.

## Ajustar el parser a tu ticket

Guarda un ticket real con `sniff --save`, añade un test con ese contenido en
`tests/test_parser.py` y ajusta los patrones de `bridge/parser.py`. Los
tickets crudos archivados en `RAW_DIR` te permiten reprocesar el histórico
con `replay` sin volver a pesar nada.
