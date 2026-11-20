# Envasadora vertical de ~1 kg — Diseño conceptual v0.1

Máquina **VFFS** (Vertical Form-Fill-Seal): toma película en bobina, la forma en tubo
alrededor de un tubo formador, sella la aleta vertical, sella el fondo, deja caer el producto,
sella la parte de arriba y corta. Es la misma arquitectura de la foto de referencia (derecha).

> Los valores marcados con ⚙ salen de `calc/dimensionamiento.py` y son **estimaciones**
> para arrancar; se confirman con `docs/plan-de-pruebas.md`.

## 1. Por qué suelen fallar estas máquinas (y cómo lo evitamos)

| Falla típica | Causa real | Qué hacemos distinto |
|---|---|---|
| Sello abre / fuga | Temperatura, presión o tiempo mal ajustados; producto en el sello; mordaza no paralela | **Probar el sello solo, en banco, antes de construir lo demás** (Fase 1). Mordazas con control PID, presión regulada y superficie serrada |
| Bolsa desalineada o corte chueco | Película que se va de lado; jalado irregular | Tubo formador **comprado** (no fabricado a mano), película con camino de rodillos y freno, jalado con motor a pasos/servo contado por encoder |
| Largo de bolsa variable | Jalado por neumático o por tiempo | Jalado por **pasos del motor** (largo en mm en la pantalla) |
| Peso variable | Dosificación por tiempo o por volumen con producto de densidad cambiante | Dosificador por **peso** (celda de carga) si el producto lo justifica |
| Todo es un solo bloque imposible de depurar | Se arma todo y luego no se sabe qué falla | **Plan por fases con prueba de aceptación en cada una** |

## 2. Especificación de partida (a confirmar)

| Parámetro | Valor de partida |
|---|---|
| Peso neto | 1.0 kg |
| Producto | Granulado / semilla, densidad ~0.7 kg/L (⚠ por confirmar) |
| Tipo de bolsa | Almohada (pillow) con sello de aleta, sin fuelle |
| Bolsa plana | Ancho 175 mm × largo 255–340 mm según densidad ⚙ (diseñar para paso máx. 350 mm) |
| Película | PE o laminado con capa sellante de PE, 60–90 µm, **ancho 360 mm** ⚙, núcleo 76 mm, Ø rollo máx. 300 mm |
| Velocidad | Objetivo 20 bolsas/min (ciclo 3 s); mecánica capaz de ~40 ⚙ |
| Alimentación | 220 V ~, aire comprimido 6–7 bar |
| Dimensiones aprox. | 800 × 900 × 2200 mm (alto: rollo arriba, tolva, tubo y mordazas) |

## 3. Arquitectura (de arriba hacia abajo)

```
        ┌───────────────┐
        │ Bobina película│  ← eje con freno + rodillo bailarín
        └──────┬────────┘
               │ camino de rodillos (3–4)
        ┌──────▼────────┐
        │ Collarín       │  ← FORMADOR COMPRADO (collarín + tubo, Ø~111 mm)
        │ formador       │
   Tolva│ ┌────────────┐ │
  + dosi│ │ Tubo de    │ │ ← el producto cae por dentro del tubo
  ficador│ │ llenado    │ │
        │ └────────────┘ │
        │  ║ barra sello │ ← sello vertical (aleta): barra caliente + cilindro
        │  ║ vertical    │
        │ ╔╩═╗ banda  ╔═╩╗│ ← jalado: 2 bandas de silicón pegadas al tubo
        │ ║  ║ jalado ║  ║│    (motor a pasos/servo)
        └─╚══╝════════╚══╝┘
          ▓▓▓ mordazas ▓▓▓  ← sello transversal + cuchilla (2 cilindros Ø63)
               │
          bolsa terminada ↓
```

### 3.1 Estructura
- **Prototipo:** perfil de aluminio ranurado 40×40 (se reconfigura sin soldar). Versión final
  en acero inoxidable 304 si va a contacto con alimento.
- Reutilizable de la máquina actual: tolva de inox, tubos, partes de lámina, soportes.

### 3.2 Desembobinado
- Eje portabobina con núcleo de 76 mm (3"), freno de fricción ajustable.
- Rodillo bailarín con resorte → mantiene tensión baja y constante.
- 3–4 rodillos locos que alinean la película con el collarín.

### 3.3 Formador (collarín + tubo)
- **Es la pieza más crítica y la más difícil de fabricar bien. Se compra** matcheado al ancho de
  película (360 mm → tubo Ø≈111 mm ⚙; el comercial más cercano es 114.3 mm, y se ajusta el ancho
  de película a ~370 mm).
- Inox, interior pulido (el producto no debe atorarse).

### 3.4 Jalado de película
- 2 bandas (silicón o hule) de ~40 mm de ancho, una a cada lado del tubo, presionadas por
  resorte/cilindro pequeño.
- Motor **NEMA 23 en lazo cerrado** (o servo) con driver; el largo de bolsa se programa en mm.
- Perfil: aceleración 8 m/s², v. máx. 0.8 m/s → 300 mm en ≈0.45 s ⚙.
- Opcional fase 2: sensor de marca de color para película impresa.

### 3.5 Sello vertical (aleta)
- Barra calefactada de ~10 mm de ancho × ~200 mm de largo, con cilindro Ø25.
- **Solo presiona cuando la película está detenida** (si se queda pegada en movimiento, quema
  y rompe la película).
- Resistencia + termopar + PID propio.

### 3.6 Sello transversal + corte (mordazas)
- 2 mordazas de aluminio, 200 mm de largo × sello de 10 mm, superficie serrada (empuja el
  producto fuera del sello), cubiertas con cinta de PTFE.
- Cada una con 2 cartuchos de 250 W + termopar + **PID + SSR** independiente (constante calor).
- Fuerza requerida ≈ 0.3–0.4 N/mm² × 2000 mm² = **600–800 N** → cilindro **Ø63×50** por
  mordaza, regulado a 3–5 bar ⚙ (Ø50 queda justo).
- Cuchilla en una mordaza accionada por cilindro Ø16 (corta al centro del sello), con
  canal/contra-cuchilla en la otra.
- Guías lineales para que ambas mordazas cierren **paralelas** (si no, el sello queda con zonas
  sin cerrar).

### 3.7 Dosificación
Decisión pendiente (depende del producto):

| Opción | Precisión | Complejidad | Cuándo |
|---|---|---|---|
| Vaso volumétrico | ±2–3 % | Baja | Producto uniforme y densidad estable |
| **Una cabeza por peso** (tolva con celda de carga + vibrador de 2 velocidades: grueso/fino) | ±0.5–1 % | Media | **Recomendada** para 1 kg |
| Sinfín | ±1 % | Media | Polvos |

El dosificador, no la mecánica, limita la velocidad (necesita pesar + descargar en < 3 s).

### 3.8 Control
- **PLC** (recomendado Schneider M221/M241, porque ya cuentas con pantalla Magelis en la
  máquina actual) + **HMI** táctil: receta (largo, temperaturas, tiempo de sello, peso).
- 3 controladores PID de temperatura (jaw frontal, jaw trasera, barra vertical) con SSR 25 A.
  La máquina actual parece tener 2 PID en el tablero: reutilizables.
- Entradas: paro de emergencia, puertas, sensor de película, sensor de bobina vacía, sensores
  magnéticos de posición en cilindros (mordazas abiertas/cerradas), celda de carga.
- Salidas: válvulas 5/2 (mordazas, barra vertical, cuchilla), motor jalado, vibradores,
  compuerta del dosificador, torreta luminosa.

### 3.9 Neumática
- Aire 6–7 bar, filtro-regulador-lubricador, regulador separado para presión de mordazas.
- Consumo ≈ 77 L/min a 20 bpm ⚙ → compresor ≥ 150 L/min con tanque ≥ 50 L.
- Válvulas 5/2 con silenciadores y estranguladores de escape (para ajustar velocidad de cierre).

### 3.10 Seguridad (no negociable)
- Paro de emergencia, protecciones fijas y **puertas con interruptor de seguridad** en zona de
  mordazas, cuchilla y bandas (referencia: ISO 12100 / ISO 13849).
- Aislamiento/guarda en superficies calientes (160 °C).
- Si estás en México, revisar además la NOM-004-STPS (protección en maquinaria).

## 4. Secuencia de ciclo

```
 Estado       Mordazas   Jalado   Barra vert.  Dosificador       Duración ⚙
 ─────────────────────────────────────────────────────────────────────────
 1 CIERRE      cerrar     parado   presiona     (pesando bolsa+1)  0.15 s
 2 SELLO       cerradas   parado   presiona     pesando            0.50 s
   + CORTE                                      (cuchilla actúa al final)
 3 APERTURA    abrir      parado   suelta       pesando            0.15 s
 4 JALADO      abiertas   avanza   suelta       DESCARGA → tubo    0.45 s
                          paso L                (producto cae)
 5 ASENTADO    abiertas   parado   suelta       pesa siguiente     0.20 s
 ─────────────────────────────────────────────────────────────────────────
 Mecánica total ≈ 1.45 s  |  Ciclo con dosificador ≈ 2.5–3.0 s (20–24 bpm)
```

Reglas de la secuencia:
1. **La película nunca se mueve con las mordazas cerradas** (interbloqueo).
2. Las mordazas cierran **solo cuando ya cayó el producto** (tiempo de caída ≈ 0.5 s) → si cierran
   con producto en el sello, hay fuga.
3. Las resistencias solo se habilitan con termopar leyendo correcto; **paro por sobretemperatura
   independiente** (termostato a ~200 °C).
4. Si no hay película, si una mordaza no llega a posición, o si la temperatura baja de la
   mínima de receta → ciclo bloqueado y alarma.

## 5. Plan por fases (resumen; detalle en `plan-de-pruebas.md`)

| Fase | Qué se construye | Prueba que debe pasar antes de continuar |
|---|---|---|
| 0 | Definir producto, película, velocidad | Muestras de película y producto en mano |
| 1 | **Banco de sello** (1 mordaza + resistencia + PID) | Sello no se abre al jalarlo ni al apretar bolsa llena |
| 2 | Bastidor + portabobina + formador + jalado + sello vertical | Fabrica tubo continuo sin que se vaya de lado, 10 m |
| 3 | Mordazas con cilindros + cuchilla, llenado a mano | 50 bolsas selladas y cortadas sin fugas |
| 4 | Dosificador por peso | 30 bolsas, error medio < 0.5 % |
| 5 | PLC + HMI + seguridad + recetas | 100 bolsas continuas sin intervención |

## 6. Riesgos principales

1. **Película equivocada** (sin capa sellante, o muy gruesa/delgada) → ninguna temperatura sirve.
   Mitigación: pedir muestra y ficha técnica del proveedor antes de diseñar el sello.
2. **Producto polvoso o grasoso** → contamina el sello. Mitigación: serrado, más tiempo/presión,
   posible extractor o soplado de aire en el tubo.
3. **Formador mal calculado** → arrugas. Mitigación: comprarlo.
4. **Velocidad ambiciosa** → empezar a 12–15 bpm y subir.

## 7. Preguntas abiertas
Ver el final de `README.md`.
