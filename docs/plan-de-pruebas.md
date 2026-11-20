# Plan de pruebas por fases

Regla: **no se pasa a la siguiente fase hasta cumplir el criterio de la actual.** Anotar cada
prueba (fecha, película, temperatura, presión, tiempo, resultado) en una tabla; esos datos son
la receta final de la máquina.

## Fase 0 — Datos de entrada
- [ ] Producto: tipo, densidad a granel (pesar 1 L), tamaño de partícula, ¿polvoso/grasoso?
- [ ] Película: tipo, ancho, espesor, **ficha técnica** (¿qué capa sella? temperatura de sello)
- [ ] 2–3 m de película de muestra para los bancos de prueba
- [ ] Velocidad objetivo (bolsas/min) y tamaño de bolsa deseado
- [ ] Inspección de lo reutilizable (ver `lista-materiales.md`)

## Fase 1 — Banco de sello (lo que más falla)
Montaje: 1 mordaza de aluminio + 2 cartuchos + termopar + PID, presionada a mano o con
cilindro; film de muestra.
- Barrido de variables: temperatura (120 → 180 °C en pasos de 10) × tiempo (0.3 → 1.0 s) × presión
  (0.2 → 0.5 N/mm²).
- Pruebas por cada combinación: **jalar a mano** el sello (debe romper la película, no el sello),
  sumergir una bolsita llena de agua y apretarla (sin burbujas/goteo).
- **Criterio de aceptación:** ventana de proceso donde 10 de 10 sellos pasan. Si la ventana es
  muy estrecha (±5 °C), revisar película o serrado.
- Medir: tiempo de calentamiento a temperatura, estabilidad (±2 °C).

## Fase 2 — Formado y jalado
Montaje: bastidor, portabobina con freno, formador comprado, bandas de jalado con motor, sello
vertical. Sin mordazas ni producto.
- Película alineada con el collarín, tubo continuo con aleta sellada.
- **Criterio:** 10 m de tubo continuo, aleta bien sellada, película centrada sin desviarse,
  largo de avance repetible (±1 mm sobre 20 avances medidos).

## Fase 3 — Mordazas + corte
Montaje: mordazas con cilindros, cuchilla, sensores. Llenado **a mano** con arroz/semilla.
- Ajustar paralelismo (papel carbón o papel de prueba entre mordazas).
- **Criterio:** 50 bolsas consecutivas selladas y cortadas, 0 fugas (prueba de apretar),
  0 cortes incompletos.

## Fase 4 — Dosificador por peso
- Calibrar celda con pesas patrón.
- **Criterio:** 30 bolsas, peso medio dentro de ±0.5 % del objetivo, desviación estándar ≤ 5 g,
  ninguna fuera de ±1.5 %.
- Si estás en México, verificar tolerancias de contenido neto (NOM-002-SCFI / NOM-030-SCFI).

## Fase 5 — Automatización completa
- PLC, HMI, recetas, interbloqueos de seguridad, alarmas.
- **Criterio:** 100 bolsas continuas a la velocidad objetivo sin intervención ni paros; prueba de
  caída (bolsa de 1 kg desde 1 m, sin reventar); paros de emergencia y puertas validados.
