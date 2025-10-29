# crazycar/car/actuation.py
from __future__ import annotations
from typing import Callable, Tuple

"""Übersetzt Regler-Outputs in Aktorik. servo_to_angle(servo) 
    wandelt einen Servowert (z. B. −100…+100) in einen Lenkwinkel in Grad, clip_steer(servo) begrenzt zulässige Ausschläge, 
    und motor_power_step(power, target) führt Power auf ein Ziel zu (sanfter Rampen-Effekt).
    Das ist die Brücke zwischen Regler und Physik."""

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
    # Totzone: -18 < fwert < 18  → Motor aus
    if -18 < fwert < 18:
        new_power = 0.0
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Vorwärts: 18 .. maxpower
    if 18 <= fwert <= maxpower:
        new_power = float(fwert)
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Rückwärts: -maxpower .. -18
    if -maxpower <= fwert <= -18:
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
