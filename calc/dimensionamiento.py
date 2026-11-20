#!/usr/bin/env python3
"""Dimensionamiento preliminar de envasadora vertical (VFFS) para ~1 kg.

Todos los parámetros se pueden cambiar por línea de comandos, p. ej.:
    python3 calc/dimensionamiento.py --producto croqueta --bpm 15

Son estimaciones de ingeniería para arrancar el diseño; se validan con las
pruebas de docs/plan-de-pruebas.md. No sustituyen el ensayo con producto real.
"""
import argparse
import math


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--producto", choices=["croqueta", "pellet"], help="atajo: croqueta=0.40 kg/L, pellet=0.65 kg/L")
    p.add_argument("--neto", type=float, default=1.0, help="peso neto por bolsa [kg]")
    p.add_argument("--densidad", type=float, default=None, help="densidad a granel del producto [kg/L]")
    p.add_argument("--ancho-bolsa", type=float, default=200, help="ancho de bolsa plana, sello a sello [mm]")
    p.add_argument("--sello", type=float, default=10, help="ancho de cada sello transversal [mm]")
    p.add_argument("--aleta", type=float, default=10, help="traslape del sello vertical (aleta) [mm]")
    p.add_argument("--espacio-libre", type=float, default=20, help="aire sobre el producto dentro de la bolsa [mm]")
    p.add_argument("--k-forma", type=float, default=0.22, help="coef. de forma de bolsa almohada (0.20-0.25)")
    p.add_argument("--espesor", type=float, default=75, help="espesor de película [um]")
    p.add_argument("--bpm", type=float, default=20, help="bolsas por minuto objetivo")
    p.add_argument("--presion-sello", type=float, default=0.40, help="presión de sello objetivo [N/mm2]")
    p.add_argument("--aire", type=float, default=5.0, help="presión de aire de trabajo [bar]")
    a = p.parse_args()
    if a.densidad is None:
        a.densidad = {"croqueta": 0.40, "pellet": 0.65}.get(a.producto, 0.40)

    print("=== 1. Volumen y geometría de bolsa ===")
    vol_prod = a.neto / a.densidad  # litros
    print(f"Volumen de producto: {vol_prod:.2f} L  ({a.neto} kg a {a.densidad} kg/L)")

    W = a.ancho_bolsa
    # V = k * W^2 * L_util  ->  L_util = V / (k W^2)
    l_util = vol_prod * 1e6 / (a.k_forma * W * W)
    largo = l_util + 2 * a.sello + a.espacio_libre
    largo = math.ceil(largo / 5) * 5
    print(f"Largo de bolsa necesario: {largo} mm (con W={W:.0f} mm, k={a.k_forma})")

    ancho_pelicula = 2 * W + a.aleta
    d_tubo = (ancho_pelicula - a.aleta) / math.pi
    print(f"Ancho de película (bobina): {ancho_pelicula:.0f} mm")
    print(f"Diámetro exterior del tubo formador: {d_tubo:.0f} mm (comerciales: 4\" = 101.6 / 4.5\" = 114.3 / 5\" = 127 mm)")

    print("\n=== 2. Bobina de película ===")
    od, core = 300.0, 76.0
    vol_rollo = math.pi / 4 * (od**2 - core**2) * ancho_pelicula  # mm3
    long_rollo = vol_rollo / (ancho_pelicula * a.espesor / 1000)  # mm
    peso_rollo = vol_rollo * 0.92e-6  # kg (PE ~0.92 g/cm3)
    paso = largo + 0  # avance de película por bolsa ~ largo de bolsa
    print(f"Rollo OD {od:.0f} / núcleo {core:.0f} mm, {a.espesor:.0f} um: ~{long_rollo/1000:.0f} m, ~{peso_rollo:.0f} kg")
    print(f"Bolsas por rollo: ~{long_rollo/paso:.0f}")
    print(f"Película por bolsa: {ancho_pelicula*paso/1e6*1000:.0f} cm2  (~{ancho_pelicula*paso*a.espesor*0.92e-9*1000:.1f} g)")

    print("\n=== 3. Tiempos de ciclo ===")
    t_cic = 60 / a.bpm
    acc, vmax = 8.0, 0.8  # m/s2, m/s
    s = paso / 1000
    d_ramp = vmax**2 / acc
    if s > d_ramp:
        t_pull = 2 * vmax / acc + (s - d_ramp) / vmax
    else:
        t_pull = 2 * math.sqrt(s / acc)
    t_close = t_open = 0.15
    t_dwell = 0.50
    t_settle = 0.20
    t_mec = t_close + t_dwell + t_open + t_pull + t_settle
    t_fall = math.sqrt(2 * 0.5 / 9.81) + 0.2
    print(f"Ciclo objetivo: {t_cic:.2f} s ({a.bpm:.0f} bpm)")
    print(f"Mecánica: cierre {t_close} + sello {t_dwell} + apertura {t_open} + jalado {t_pull:.2f} + asentado {t_settle} = {t_mec:.2f} s  -> máx {60/t_mec:.0f} bpm")
    print(f"Caída de producto por tubo (~0.5 m + compuerta): ~{t_fall:.2f} s (ocurre durante el jalado)")
    print(f"Dosificador debe completar pesada+descarga en < {t_cic:.2f} s  (cuello de botella real)")
    v_pico = vmax
    rev_s = v_pico / (math.pi * 0.060)
    print(f"Jalado: v pico {v_pico} m/s; con rodillo/polea de Ø60 mm -> {rev_s*60:.0f} rpm pico, {paso/ (math.pi*60):.2f} vueltas por bolsa")

    print("\n=== 4. Mordazas de sello transversal ===")
    L_mord = W + 25
    area = L_mord * a.sello
    F_req = a.presion_sello * area
    print(f"Mordaza: largo {L_mord:.0f} mm x sello {a.sello:.0f} mm = {area:.0f} mm2")
    print(f"Fuerza de cierre requerida a {a.presion_sello} N/mm2: {F_req:.0f} N")
    for d in (40, 50, 63):
        F = math.pi / 4 * d**2 * a.aire / 10 * 0.85  # N, 85% eficiencia
        ok = "OK" if F >= F_req * 1.15 else "justo/insuficiente"
        print(f"  Cilindro Ø{d} a {a.aire} bar: {F:.0f} N  -> {ok}")
    masa_mord = 0.8  # kg aluminio aprox
    dT = 160 - 20
    e_calent = masa_mord * 900 * dT / 1000  # kJ
    print(f"Calentamiento por mordaza (~{masa_mord} kg Al a 160 C): {e_calent:.0f} kJ -> con 2x250 W ~{e_calent*1000/500/60:.1f} min (+pérdidas, esperar ~5-8 min)")

    print("\n=== 5. Aire comprimido ===")
    def cons(d, carrera, ciclos=1):
        v = math.pi / 4 * (d / 10) ** 2 * (carrera / 10) / 1000  # L
        return v * (1 + a.aire) * 2 * 0.9 * ciclos  # ida y vuelta
    q_cic = 2 * cons(63, 50) + cons(25, 30) + cons(16, 25) + cons(32, 30)
    print(f"Consumo por ciclo ~{q_cic:.1f} L libres -> {q_cic*a.bpm:.0f} L/min a {a.bpm:.0f} bpm")
    print(f"Compresor recomendado: >= {max(150, q_cic*a.bpm*2):.0f} L/min con tanque >= 50 L, a >= 7 bar")


if __name__ == "__main__":
    main()
