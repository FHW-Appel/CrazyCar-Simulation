# crazycar/car/actuation.py
"""Actuation/Control: Steering angle and motor/reverse logic (pygame-free)."""

from __future__ import annotations
from typing import Callable, Tuple
import os
import logging

# Configurable deadzone/min-start via environment for easier testing:
_LOG = logging.getLogger("crazycar.car.actuation")
DEADZONE = float(os.getenv("CRAZYCAR_MOTOR_DEADZONE", "18"))
MIN_START_PERCENT = float(os.getenv("CRAZYCAR_MIN_START_PERCENT", "0.08"))

# Type for a speed function that calculates current vehicle speed
# from a power value (e.g., from model.Car).
# Signature intentionally lean: speed_fn(power) -> speed_px
SpeedFn = Callable[[float], float]

# Type for a delay function (e.g., timeutil.delay_ms)
DelayFn = Callable[[int], None]


def servo_to_angle(servo_wert: float) -> float:
    """Convert servo setpoint to actual steering angle.
    
    Maps servo control value to physical steering angle using quadratic formula.
    Corresponds to previous 'servo2IstWinkel' formula including sign handling.
    
    Args:
        servo_wert: Servo setpoint value (can be negative for left turn)
        
    Returns:
        Actual steering angle in degrees (negative = left, positive = right)
        
    Note:
        Formula uses empirically determined coefficients:
        angle = 0.03*x² + 0.97*x + 2.23 (from servo calibration)
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
    """Limit steering angle to physical constraints.
    
    Clamps steering angle to prevent exceeding vehicle's maximum steering capability.
    Corresponds to previous 'getwinkel' function.
    
    Args:
        swert: Requested steering angle in degrees
        min_deg: Minimum allowed angle (default: -10.0° for left)
        max_deg: Maximum allowed angle (default: 10.0° for right)
        
    Returns:
        Clamped steering angle within [min_deg, max_deg] range
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
    Encapsulates getmotorleistung()/ruckfahren() behavior.

    Args:
        fwert:         Requested drive power (throttle), can be negative (reverse).
        current_power: Currently applied power value at vehicle.
        current_speed_px: Current speed [px/step], affected by speed_fn.
        maxpower:      Maximum allowed power (e.g., 100).
        speed_fn:      Callback: new_speed_px = speed_fn(power). Uses internal state (e.g., radangle).
        delay_fn:      Callback for short delays (e.g., 10 ms).

    Returns:
        (new_power, new_speed_px)
    """
    # Deadzone: configurable via CRAZYCAR_MOTOR_DEADZONE (default 18)
    if -DEADZONE < fwert < DEADZONE:
        new_power = 0.0
        new_speed = speed_fn(new_power)
        _LOG.debug("apply_power: fwert=%.1f within deadzone=%.1f -> power=0", fwert, DEADZONE)
        return new_power, new_speed

    # Forward: 18 .. maxpower
    if DEADZONE <= fwert <= maxpower:
        # Allow a minimal start percentage to overcome static friction if configured
        if 0 < fwert < (maxpower * MIN_START_PERCENT):
            new_power = float(maxpower * MIN_START_PERCENT)
            _LOG.debug("apply_power: fwert=%.1f < min_start -> using min_start%%=%.3f => power=%.2f", fwert, MIN_START_PERCENT, new_power)
        else:
            new_power = float(fwert)
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Reverse: -maxpower .. -18
    if -maxpower <= fwert <= -DEADZONE:
        # Kickback/coast sequence if forward power is still applied
        if current_power > 0:
            # Short counter-thrust
            tmp_power = -30.0  # Brief reverse power to brake forward momentum
            _ = speed_fn(tmp_power)
            delay_fn(10)  # 10 ms brake duration

            # Coast
            tmp_power = 0.0
            _ = speed_fn(tmp_power)
            delay_fn(10)  # 10 ms coast phase before reverse

        # Then set desired reverse power
        new_power = float(fwert)
        new_speed = speed_fn(new_power)
        return new_power, new_speed

    # Outside limits: no change (fail-safe)
    return float(current_power), float(current_speed_px)


__all__ = ["servo_to_angle", "clip_steer", "apply_power", "SpeedFn", "DelayFn"]
