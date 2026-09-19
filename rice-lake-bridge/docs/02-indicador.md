# Configuración del indicador Rice Lake 480 Legend

> Los nombres exactos de los menús varían entre versiones de firmware.
> **Confirma contra el manual técnico de tu equipo** antes de cambiar nada,
> y anota los valores actuales para poder revertir.

## 1. Anota los parámetros actuales (no los cambies todavía)

Entra al menú de configuración y busca el grupo **SERIAL** del puerto que
alimenta la impresora. Necesitas estos valores:

| Parámetro | Típico | Para qué lo necesitas |
|---|---|---|
| `BAUD`    | 9600 | → `SCALE_BAUDRATE` |
| `BITS`    | 8 sin paridad (a veces 7-par) | → `SCALE_BYTESIZE` / `SCALE_PARITY` |
| `STOPBITS`| 1 | → `SCALE_STOPBITS` |
| `TERMIN`  | CR/LF | cómo termina cada línea |
| `HANDSHK` | none / XON-XOFF / hardware | decide si el modo en línea es viable |
| `EOLDLY`  | 0 | retardo entre líneas |

**El puente debe usar exactamente estos mismos valores.** Un baudrate
distinto es la causa del 90 % de los "recibo basura ilegible".

Lo ideal es no tocar nada en el indicador: el puente se adapta a lo que ya
está configurado, porque la impresión debe seguir funcionando igual.

## 2. Formato del ticket

El 480 imprime con un formato configurable (grupo **PFORMT**, con plantillas
tipo `GFMT` / `NFMT` / `TFMT`). El parser reconoce automáticamente las
etiquetas en español e inglés:

- `BRUTO` / `GROSS`
- `TARA` / `TARE`
- `NETO` / `NET`
- `Ticket`, `Folio`, `Boleta`, `Comprobante` → número de ticket
- `Placa`, `Patente`, `Camión`, `Unidad`, `ID` → identificador del vehículo

Si tu formato usa otras etiquetas, ajusta los patrones en
`bridge/parser.py` (`_FIELD_PATTERNS`, `_TICKET_NO_RE`, `_VEHICLE_RE`) y
añade un test con tu ticket real en `tests/test_parser.py`.

Cualquier línea con forma `Etiqueta: valor` que el parser no reconozca **no
se pierde**: queda en el campo `extra` del payload, y el texto completo del
ticket viaja siempre en `text` y en `raw_b64`.

## 3. Caja suma (junction box)

La caja suma solo combina las celdas de carga y entrega **una** señal de peso
al indicador. No interviene en la comunicación serie: para este proyecto es
transparente. La calibración y el reparto entre celdas siguen siendo trabajo
del indicador y no los toca el puente.

## 4. Alternativa: segundo puerto serie

Algunas configuraciones del 480 traen un segundo puerto o una ranura de
expansión. Si tu equipo lo tiene, la opción más limpia de todas es dejar la
impresora en el puerto 1 y configurar el puerto 2 en **salida por demanda**
(demand) con el mismo formato de ticket: conectas el Pi ahí y no hay ningún
tap, ninguna derivación y ningún riesgo sobre la impresión.

Revisa en el menú si aparece un `PORT 2` / `SERIAL 2`. Si existe, úsalo.
