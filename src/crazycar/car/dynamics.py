# crazycar/car/dynamics.py
"""Fahrdynamik: Sollgeschwindigkeit & Geschwindigkeits-Update (pygame-frei).

Abbildungen aus dem Original:
- soll_speed(power)                -> Zielgeschwindigkeit (sim-Pixel/Step)
- step_speed(v_px, power, rad_deg) -> neue Geschwindigkeit (sim-Pixel/Step)

Hinweise:
- Rechnet intern in Realwerten (cm/s) und konvertiert über units.py.
- Zeitinkrement dt ist standardmäßig 0.01 (wie im Originalcode).

Kümmert sich um Geschwindigkeit, Beschleunigung und Dämpfung. 
apply_power(power, v, dt, drag, vmax) aktualisiert die Geschwindigkeit 
mit einfacher Luft-/Rollreibung und einem Maximalwert, accel_from_power(power) 
gibt die momentane Beschleunigung zurück. 
Das Modul bildet die einfache Längsdynamik des Fahrzeugs.
"""

from __future__ import annotations
from typing import Tuple

from .units import sim_to_real, real_to_sim


def _max_speed_cm_s(power: float, radangle_deg: float) -> float:
    """Maximalgeschwindigkeit in cm/s gemäß Originalformeln."""
    p = abs(power)
    if radangle_deg < 5:
        # Geradeaus-Formel
        vmax = -0.0496 * (p ** 2) + 9.008 * p + 31.8089
        vmax /= 100.0
    else:
        # Kurven-Formel
        vmax = -81562.0 * (p ** (-2.47)) + 215.5123
        vmax /= 100.0
    return float(vmax)


def _acceleration_cm_s2(speed_cm_s: float, power: float) -> float:
    """Beschleunigung in cm/s² gemäß Originalformel (linear in v, quadratisch in power)."""
    p = abs(power)
    a = -2.179 * speed_cm_s + 0.155 * (p ** 2) + 7.015 * p
    a /= 100.0
    return float(a)


def soll_speed(power: float) -> float:
    """Sollgeschwindigkeit (sim-Pixel/Step) für gegebenen Power-Wert (Vorzeichen berücksichtigt)."""
    # Original-Geradeausformel
    v_cm_s = (-0.0496 * (power ** 2) + 9.008 * power + 31.8089) / 100.0
    return real_to_sim(v_cm_s)


def step_speed(
    current_speed_px: float,
    power: float,
    radangle_deg: float,
    *,
    dt: float = 0.01,
) -> float:
    """Ein Schritt Geschwindigkeits-Update (sim-Pixel/Step) gemäß Original 'Geschwindigkeit'.

    Args:
        current_speed_px: aktuelle Geschwindigkeit in Sim-Pixel/Step
        power:            Antriebsleistung (kann negativ sein → Rückwärts)
        radangle_deg:     Lenkwinkel in Grad
        dt:               Zeitschritt (Standard 0.01 wie im Original)
    """
    # In Real-Größe (cm/s) wechseln
    v = sim_to_real(current_speed_px)

    # Vorzeichenlogik wie im Original: negative Power invertiert Vorzeichenrechnung
    turnback = False
    p = power
    if p < 0:
        p = -p
        v = -v
        turnback = True

    if p == 0:
        v_new = 0.0
    else:
        vmax = _max_speed_cm_s(p, radangle_deg)
        a = _acceleration_cm_s2(v, p)

        # Euler-Schritt mit Begrenzung auf vmax (Betrag)
        v_candidate = v + a * dt
        if abs(v_candidate) <= abs(vmax):
            v_new = v_candidate
        else:
            # Wenn Überschreiten, einfach am Limit klemmen
            v_new = vmax if v >= 0 else -vmax

    # Zurück in Sim-Einheiten
    sim_v = real_to_sim(v_new if not turnback else -v_new)
    return float(sim_v)


__all__ = ["soll_speed", "step_speed"]
