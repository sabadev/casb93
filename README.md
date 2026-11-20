# casb93 — Envasadora vertical de ~1 kg

Proyecto de diseño y construcción de una envasadora vertical (VFFS) de bolsa de película
sellada térmicamente, para ~1 kg por bolsa. Se parte de cero y se reutilizan piezas de la
máquina anterior solo cuando se verifique que sirven.

## Contenido
- [`docs/diseno-conceptual.md`](docs/diseno-conceptual.md) — arquitectura, secuencia de ciclo, riesgos
- [`docs/lista-materiales.md`](docs/lista-materiales.md) — BOM preliminar y qué se puede reutilizar
- [`docs/plan-de-pruebas.md`](docs/plan-de-pruebas.md) — construcción por fases con criterios de aceptación
- [`calc/dimensionamiento.py`](calc/dimensionamiento.py) — calculadora paramétrica (bolsa, película, tiempos, fuerza de sello, aire)

```bash
python3 calc/dimensionamiento.py --producto croqueta --bpm 15
python3 calc/dimensionamiento.py --producto pellet --bpm 20
```

## Preguntas abiertas (cambian el diseño)
1. ~~Producto~~ ✅ croquetas para mascota y pellet para ganado. **Falta:** peso real de 1 L de cada uno, tamaño de pieza y si tienen mucho polvo/grasa.
2. **¿Qué película tienes o piensas usar?** (material, ancho, espesor) → define temperaturas y ancho del formador.
3. **¿Cuántas bolsas por minuto necesitas** y cuál es el presupuesto aproximado?
4. **¿Qué sirve de la máquina actual?** (PLC/HMI, PIDs, cilindros, tolva, compresor).
5. **Alimentación disponible:** ¿220 V monofásico o trifásico? ¿Compresor de taller?
6. **¿Bolsa tipo almohada simple o con impresión/fecha/fuelle?**
