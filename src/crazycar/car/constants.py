# crazycar/car/constants.py
from __future__ import annotations
import os
import logging

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
# Bildschirm-/Skalierungsfaktoren
# ------------------------------------------------------------
f: float = 0.8
WIDTH: int  = int(1920 * f)
HEIGHT: int = int(1080 * f)

# ------------------------------------------------------------
# Farben (werden von model/simulation genutzt)
# ------------------------------------------------------------
BORDER_COLOR: tuple[int, int, int, int]      = (255, 255, 255, 255)  # Streckenrand (Crash)
FINISH_LINE_COLOR: tuple[int, int, int, int] = (237, 28, 36, 255)    # Ziellinie (Rot)

# ------------------------------------------------------------
# Radar-Defaults (für sensors.py)
# ------------------------------------------------------------
# Standard-Sweep ±60° (wie im ursprünglichen Code)
RADAR_SWEEP_DEG: int = 60
# Maximale Radar-Länge relativ zur Streckenbreite (130cm auf 1900cm)
MAX_RADAR_LEN_RATIO: float = 130.0 / 1900.0

# ------------------------------------------------------------
# Realmaße in cm (Defaults)
# ------------------------------------------------------------
_CAR_X_CM: float      = 40.0
_CAR_Y_CM: float      = 20.0
_RADSTAND_CM: float   = 25.0
_SPURWEITE_CM: float  = 10.0

# ------------------------------------------------------------
# Abgeleitete Pixelgrößen (werden durch init_pixels() gesetzt)
# ------------------------------------------------------------
CAR_SIZE_X: float = 0.0
CAR_SIZE_Y: float = 0.0
CAR_cover_size: int = 0
CAR_Radstand: float = 0.0
CAR_Spurweite: float = 0.0


def init_pixels(real_to_sim) -> None:
    """
    Rechnet Realmaße (cm) in Pixel um. Muss genau einmal
    nach dem Import des Konverters aufgerufen werden.
    """
    global CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size, CAR_Radstand, CAR_Spurweite

    try:
        CAR_SIZE_X     = float(real_to_sim(_CAR_X_CM))
        CAR_SIZE_Y     = float(real_to_sim(_CAR_Y_CM))
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
        CAR_Radstand   = float(real_to_sim(_RADSTAND_CM))
        CAR_Spurweite  = float(real_to_sim(_SPURWEITE_CM))
    except Exception as e:
        log.error("init_pixels: Fehler beim Umrechnen (%r). Fallback auf Defaults.", e)
        CAR_SIZE_X, CAR_SIZE_Y = 32.0, 16.0
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
        CAR_Radstand, CAR_Spurweite = 25.0, 10.0
        return

    # Guards gegen 0/NaN
    if not (CAR_SIZE_X > 0.0 and CAR_SIZE_Y > 0.0):
        log.error("CAR_SIZE_* ist 0/negativ. Fallback auf 32x16 px.")
        CAR_SIZE_X, CAR_SIZE_Y = 32.0, 16.0
        CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
    if not (CAR_Radstand > 0.0 and CAR_Spurweite > 0.0):
        log.error("Radstand/Spurweite ist 0/negativ. Fallback auf 25/10 px.")
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
