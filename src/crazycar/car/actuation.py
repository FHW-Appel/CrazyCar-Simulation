# crazycar/car/actuation.py
"""Aktorik/Ansteuerung: Lenkwinkel- und Motor-/Rückwärtslogik (pygame-frei)."""

from __future__ import annotations
from typing import Callable, Tuple
import os
import logging

# Configurable deadzone/min-start via environment for easier testing:
_LOG = logging.getLogger("crazycar.car.actuation")
DEADZONE = float(os.getenv("CRAZYCAR_MOTOR_DEADZONE", "18"))
MIN_START_PERCENT = float(os.getenv("CRAZYCAR_MIN_START_PERCENT", "0.08"))

# Typ für eine Geschwindigkeitsfunktion, die (z. B. aus model.Car) die aktuelle
# Fahrzeug-Geschwindigkeit aus einem Power-Wert berechnet.
# Signatur bewusst schlank: speed_fn(power) -> speed_px
SpeedFn = Callable[[float], float]

# Typ für eine Delay-Funktion (z. B. timeutil.delay_ms)
DelayFn = Callable[[int], None]


def servo_to_angle(servo_wert: float) -> float:
    """
    Abbildung Servo-Sollwert → Ist-Lenkwinkel (Grad).
    Entspricht deiner bisherigen 'servo2IstWinkel'-Formel inkl. Vorzeichenbehandlung.
    """
    flag = servo_wert < 0
    if flag:
        servo_wert = -servo_wert
    if servo_wert == 0:
        winkel = 0.0
    else:
        winkel = 0.03 * servo_wert * servo_wert + 0.97 * servo_wert + 2.23
    return -winkel if flag else winkel


def clip_steer(swert: float, min_deg: float = -10.0, max_deg: float = 10.0) -> float:
    """
    Begrenzung des Lenkwinkels in Grad (entspricht 'getwinkel').
    """
    if swert == 0:
        return 0.0
    if swert >= max_deg:
        return float(max_deg)
    if swert <= min_deg:
        return float(min_deg)
    return float(swert)


def apply_power(
    fwert: float,
    current_power: float,
    current_speed_px: float,
    maxpower: float,
    speed_fn: SpeedFn,
    delay_fn: DelayFn,
) -> Tuple[float, float]:
    """
    Kapselt getmotorleistung()/ruckfahren()-Verhalten.

    Args:
        fwert:         Geforderte Antriebsleistung (Throttle), kann negativ sein (Rückwärts).
        current_power: Der aktuell am Fahrzeug anliegende Power-Wert.
        current_speed_px: Aktuelle Geschwindigkeit [px/step], wird von speed_fn beeinflusst.
        maxpower:      Maximale zulässige Leistung (z. B. 100).
        speed_fn:      Callback: new_speed_px = speed_fn(power). Nutzt internen State (z. B. radangle).
        delay_fn:      Callback für kurze Verzögerungen (z. B. 10 ms).

    Returns:
        (new_power, new_speed_px)
    """
    # Totzone: configurable via CRAZYCAR_MOTOR_DEADZONE (default 18)
    if -DEADZONE < fwert < DEADZONE:
        new_power = 0.0
        new_speed = speed_fn(new_power)
        _LOG.debug("apply_power: fwert=%.1f within deadzone=%.1f -> power=0", fwert, DEADZONE)
        return new_power, new_speed

    # Vorwärts: 18 .. maxpower
    if DEADZONE <= fwert <= maxpower:
        # Allow a minimal start percentage to overcome static friction if configured
        if 0 < fwert < (maxpower * MIN_START_PERCENT):
            new_power = float(maxpower * MIN_START_PERCENT)
            _LOG.debug("apply_power: fwert=%.1f < min_start -> using min_start%%=%.3f => power=%.2f", fwert, MIN_START_PERCENT, new_power)
        else:
            new_power = float(fwert)
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Rückwärts: -maxpower .. -18
    if -maxpower <= fwert <= -DEADZONE:
        # Rückstoß-/Freilauf-Sequenz, falls aktuell noch Vorwärtsleistung anliegt
        if current_power > 0:
            # kurzer Gegenschub
            tmp_power = -30.0
            _ = speed_fn(tmp_power)
            delay_fn(10)

            # Freilauf
            tmp_power = 0.0
            _ = speed_fn(tmp_power)
            delay_fn(10)

        # danach gewünschte Rückwärtsleistung setzen
        new_power = float(fwert)
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Außerhalb der Grenzen: keine Änderung (Fail-safe)
    return float(current_power), float(current_speed_px)


__all__ = ["servo_to_angle", "clip_steer", "apply_power", "SpeedFn", "DelayFn"]
