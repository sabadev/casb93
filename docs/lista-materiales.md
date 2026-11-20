# Lista de materiales preliminar (BOM) v0.1

Sin precios (hay que cotizar con proveedores locales). La columna **Reusar** se basa en lo
visible en la foto de la máquina actual (marca Strokmatic): hay que **inspeccionar físicamente**
cada pieza antes de confirmarla.

Leyenda Reusar: ✅ probable · ❓ revisar · ❌ comprar nuevo

## Estructura
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| Perfil de aluminio ranurado 40×40 + escuadras | Para bastidor del prototipo | ~20 m | ❌ |
| Tolva de inox | Capacidad ≥ 15 L (croqueta es voluminosa) | 1 | ✅ (tolva actual) |
| Lámina y soportes | Inox/acero | — | ❓ |
| Protecciones con ventana | Policarbonato o lámina, con puertas | 1 juego | ❌ |

## Película y formado
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| Collarín + tubo formador | Para película 410 mm, tubo Ø127 mm (5"), inox 304, interior pulido | 1 | ❌ **comprar** |
| Portabobina con freno | Núcleo 76 mm, Ø máx. 300 mm, ~25 kg, ancho 410 mm | 1 | ❌ |
| Rodillos locos + bailarín | Aluminio/inox Ø30–40 × 450 mm | 4 + 1 | ❌ |
| Bandas de jalado | Silicón/hule 40 mm × ~250 mm | 2 | ❌ |

## Sellado
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| Mordazas de aluminio | 225 mm largo, sello 10–12 mm serrado, ranura para cuchilla | 2 | ❌ (maquinar) |
| Cartuchos calefactores | Ø10 × 100–150 mm, 250 W, 220 V | 4 | ❌ |
| Termopar tipo K (o J) | Para cada mordaza | 2 | ❌ |
| Barra de sello vertical | 10 × 225 mm + cartucho 250 W + termopar | 1 | ❌ |
| Cinta PTFE adhesiva | Alta temperatura, 0.13 mm | 1 rollo | ❌ |
| Cuchilla serrada | Acero inox, ~225 mm | 2 | ❌ |
| Guías lineales | Para cada mordaza (carrera ~50 mm) | 4 | ❓ |

## Neumática
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| Cilindro mordazas | Ø63 × 50 mm, doble efecto, con imán | 2 | ❓ (los cilindros actuales pueden ser más chicos) |
| Cilindro barra vertical | Ø25 × 30 mm | 1 | ❓ |
| Cilindro cuchilla | Ø16 × 25 mm | 1 | ❓ |
| Cilindro presión de bandas | Ø32 × 30 mm (o resorte) | 1 | ❓ |
| Electroválvulas 5/2 | 24 VDC | 4 | ❓ |
| Regulador mordazas + FRL | 0–8 bar | 1 + 1 | ❌ |
| Sensores magnéticos de posición | Para cilindros de mordazas | 4 | ❌ |
| Compresor | ≥ 150 L/min, tanque ≥ 50 L | 1 | ❓ |

## Dosificación
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| Tolva de pesaje | Inox ≥ 4–5 L con compuerta neumática de apertura rápida | 1 | ❌ |
| Celda de carga | 5–10 kg, clase C3 o mejor | 1 | ❌ |
| Transmisor de peso | 24 bits, Modbus RTU | 1 | ❌ |
| Alimentador vibratorio | Charola, 2 velocidades (grueso/fino), descarga suave | 1 | ❌ |
| Criba/tamiz de finos | Antes de la tolva (quita polvo del pellet) | 1 | ❌ |
| Soplador de aire o extracción de polvo | En zona de sello | 1 | ❌ |

## Electricidad y control
| Ítem | Especificación | Cant. | Reusar |
|---|---|---|---|
| PLC | Schneider M221 (o el que ya tengas) con salidas a transistor | 1 | ❓ |
| HMI táctil | Magelis (visible en la máquina actual) | 1 | ✅ |
| Controladores PID de temperatura | 1/16 DIN, salida SSR | 3 | ✅ (hay 2 en el tablero) |
| Relevadores de estado sólido (SSR) | 25 A, 220 V | 3 | ❌ |
| Motor a pasos NEMA 23 lazo cerrado + driver | ≥ 2 Nm | 1 | ❌ |
| Fuente 24 VDC | 10 A | 1 | ❓ |
| Paro de emergencia + interruptores de seguridad de puertas | Cat. 1–3 | 1 + 2 | ✅ (paro) / ❌ |
| Torreta luminosa | Rojo/verde/ámbar | 1 | ✅ |
| Termostato de sobretemperatura | ~200 °C, independiente del PID | 3 | ❌ |
| Sensor de película / de fin de bobina | Óptico/capacitivo | 2 | ❌ |
| Conectores industriales, canaletas, cable | — | — | ✅ parcial |
