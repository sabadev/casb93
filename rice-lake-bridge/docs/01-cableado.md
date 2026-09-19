# Cableado: cómo intervenir el cable indicador → Epson

El indicador **manda** los bytes del ticket por su línea TX y la impresora
los **recibe** por su RX. Es un flujo de una sola dirección: nosotros solo
tenemos que escuchar esa línea.

Hay dos formas de hacerlo. **Empieza por la A.**

---

## Opción A — Tap pasivo (recomendada)

El cable actual **no se toca**. Se conecta un segundo receptor en paralelo
sobre la línea TX.

```
  Rice Lake 480          cable actual              Epson matricial
   [ TX ]───────┬──────────────────────────────────────▶[ RX ]
   [ GND ]──────┼──┬───────────────────────────────────▶[ GND ]
                │  │
                │  │   (derivación nueva, solo escucha)
                ▼  ▼
        ┌──────────────────┐
        │ RX (pin 2)  GND  │   adaptador USB-RS232 (DB-9 hembra)
        │      TX  ── N/C  │   ← el TX del adaptador NO se conecta
        └────────┬─────────┘
                 │ USB
          ┌──────▼──────┐
          │ Raspberry Pi│  ← aquí corre el puente
          └─────────────┘
```

**Ventaja decisiva:** si el Pi se apaga, se cuelga o lo desconectas, la
báscula sigue imprimiendo exactamente igual. No introduces un punto de falla
en una operación de pesaje que ya funciona.

### Pinout

| Señal | DB-9 | DB-25 | Conectar a |
|---|---|---|---|
| TX del indicador | pin 3 | pin 2 | **RX del adaptador** (pin 2 en DB-9) |
| GND | pin 5 | pin 7 | **GND del adaptador** (pin 5 en DB-9) |
| TX del adaptador | — | — | **dejar al aire** |

En la foto, el capuchón gris del indicador es un **DB-25**: TX = pin 2,
GND = pin 7. Confirma con multímetro antes de soldar.

Lo más limpio es un **repartidor RS-232 en Y** o una regleta en el capuchón;
si haces empalme directo, usa termorretráctil y no dejes el hilo al aire.

### La advertencia que importa

Dos receptores RS-232 en paralelo cargan la línea (cada entrada son 3–7 kΩ;
en paralelo quedan ~1,5–3,5 kΩ, y el estándar solo garantiza 3 kΩ). A 9600
baudios y con cables cortos funciona sin problema en la práctica, **pero
verifícalo**: imprime un ticket de prueba con el tap conectado y comprueba
que la Epson lo saca íntegro y que el `sniff` recibe el mismo texto. Si la
impresión sale con caracteres corridos, pásate a la opción B o intercala un
buffer/splitter RS-232 alimentado.

---

## Opción B — En línea (passthrough)

El puente queda en medio y reenvía cada byte a la impresora.

```
 Rice Lake 480 ──▶ USB-RS232 #1 ──▶ [ Raspberry Pi ] ──▶ USB-RS232 #2 ──▶ Epson
```

Se activa poniendo `PRINTER_PORT` en el `.env`. El servicio escribe a la
impresora **antes** de procesar el ticket, así la impresión no espera al
backend. El test `test_modo_en_linea_reenvia_los_bytes_intactos_a_la_impresora`
verifica que los bytes llegan idénticos, códigos ESC/P incluidos.

**Desventajas reales, tenlas presentes:**

1. Si el Pi se cae, **la báscula deja de imprimir**. Es un punto de falla
   nuevo en una operación crítica.
2. Si hoy el indicador y la impresora usan **control de flujo por hardware**
   (la Epson baja DTR/CTS cuando se le llena el búfer), dos adaptadores USB
   independientes **no propagan esas líneas**. Tendrías que pasar ambos
   extremos a XON/XOFF (`SCALE_XONXOFF=true`) o volver a la opción A.

Usa esta opción solo si el tap pasivo te dio problemas de señal.

---

## Hardware sugerido

- **Raspberry Pi 4** (o cualquier mini PC con Linux). Con fuente decente y,
  si el corte de luz es frecuente en la báscula, un UPS pequeño.
- **Adaptador USB-RS232 con chip FTDI genuino.** Evita los clones baratos
  de PL2303/CH340: son la causa número uno de bytes perdidos en estas
  instalaciones.
- Un DB-25 macho/hembra con bornera de tornillo para hacer la derivación
  sin cortar el cable original.

## Nombre fijo del puerto

Si conectas dos adaptadores, `/dev/ttyUSB0` y `/dev/ttyUSB1` pueden
intercambiarse al reiniciar. Usa la ruta estable:

```bash
ls -l /dev/serial/by-id/
# usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0 -> ../../ttyUSB0
```

Esa ruta completa va en `SCALE_PORT`. También puedes fijar un alias con la
regla udev incluida en `systemd/99-rice-lake.rules`.
