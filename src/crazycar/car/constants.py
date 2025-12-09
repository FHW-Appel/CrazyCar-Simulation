# crazycar/car/constants.py
from __future__ import annotations
import os
import logging

"""Bündelt alle festen Simulations- und Fahrzeugparameter. 
    Hier stehen Fenstergröße (WIDTH, HEIGHT), der globale Skalierungsfaktor f,
    Farbdefinitionen (COLORS), Fahrzeugmaße (CAR), Sensor-Layout (SENSOR), einfache Physik-Grenzen (PHYS) sowie die Ziellinie (FINISH_LINE). Nichts “lebt” hier—es sind reine Konstanten, die die übrigen Module konfigurieren."""

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.constants")

# ------------------------------------------------------------
# Screen/scaling factors
# ------------------------------------------------------------
f: float = 0.8
WIDTH: int  = int(1920 * f)
HEIGHT: int = int(1080 * f)

# ------------------------------------------------------------
# Colors (used by model/simulation)
# ------------------------------------------------------------
BORDER_COLOR: tuple[int, int, int, int]      = (255, 255, 255, 255)  # Track border (crash)
FINISH_LINE_COLOR: tuple[int, int, int, int] = (237, 28, 36, 255)    # Finish line (red)

# ------------------------------------------------------------
# Radar defaults (for sensors.py)
# ------------------------------------------------------------
# Standard sweep ±60° (as in original code)
RADAR_SWEEP_DEG: int = 60
# Maximum radar length relative to track width (130cm on 1900cm)
MAX_RADAR_LEN_RATIO: float = 130.0 / 1900.0

# ------------------------------------------------------------
# Real-world dimensions in cm (defaults)
# ------------------------------------------------------------
_CAR_X_CM: float      = 40.0
_CAR_Y_CM: float      = 20.0
_RADSTAND_CM: float   = 25.0
_SPURWEITE_CM: float  = 10.0

# ------------------------------------------------------------
# Derived pixel sizes (set by init_pixels())
# ------------------------------------------------------------
CAR_SIZE_X: float = 0.0
CAR_SIZE_Y: float = 0.0
CAR_cover_size: int = 0
CAR_Radstand: float = 0.0
CAR_Spurweite: float = 0.0


def init_pixels(real_to_sim) -> None:
    """
    Convert real-world dimensions (cm) to pixels. Must be called exactly once
    after importing the converter.
    """
    global CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size, CAR_Radstand, CAR_Spurweite

    # Perform conversion: Real dimensions (cm) → Pixels
    try:
        CAR_SIZE_X     = float(real_to_sim(_CAR_X_CM))
        CAR_SIZE_Y     = float(real_to_sim(_CAR_Y_CM))
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
        CAR_Radstand   = float(real_to_sim(_RADSTAND_CM))
        CAR_Spurweite  = float(real_to_sim(_SPURWEITE_CM))
    except Exception as e:
        log.error("init_pixels: Fehler beim Umrechnen (%r). Fallback to defaults.", e)
        # Fallback values for robust simulation (typical 32x16px sprite size)
        FALLBACK_CAR_X = 32.0
        FALLBACK_CAR_Y = 16.0
        FALLBACK_RADSTAND = 25.0
        FALLBACK_SPURWEITE = 10.0
        CAR_SIZE_X, CAR_SIZE_Y = FALLBACK_CAR_X, FALLBACK_CAR_Y
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
        CAR_Radstand, CAR_Spurweite = FALLBACK_RADSTAND, FALLBACK_SPURWEITE
        return

    # Validation: Guards against 0/NaN/negative values
    if not (CAR_SIZE_X > 0.0 and CAR_SIZE_Y > 0.0):
        log.error("CAR_SIZE_* is 0/negative. Fallback to 32x16 px.")
        CAR_SIZE_X, CAR_SIZE_Y = 32.0, 16.0
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
    if not (CAR_Radstand > 0.0 and CAR_Spurweite > 0.0):
        log.error("Radstand/Spurweite is 0/negative. Fallback to 25/10 px.")
        CAR_Radstand, CAR_Spurweite = 25.0, 10.0

    if os.getenv("CRAZYCAR_DEBUG") == "1":
        log.info(
            "PIXELS: size_x=%.2f size_y=%.2f cover=%d radstand=%.2f spurweite=%.2f WIDTH=%d HEIGHT=%d",
            CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size, CAR_Radstand, CAR_Spurweite, WIDTH, HEIGHT
        )


__all__ = [
    "f", "WIDTH", "HEIGHT",
    "BORDER_COLOR", "FINISH_LINE_COLOR",
    "RADAR_SWEEP_DEG", "MAX_RADAR_LEN_RATIO",
    "CAR_SIZE_X", "CAR_SIZE_Y", "CAR_cover_size",
    "CAR_Radstand", "CAR_Spurweite",
    "init_pixels",
]
