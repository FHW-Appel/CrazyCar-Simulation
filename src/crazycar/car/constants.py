# src/crazycar/car/constants.py
"""Zentrale Konstanten für CrazyCar (pygame-frei)."""

# --- Skalierung & Trackgröße ---
f: int = 1
WIDTH: int = 1920 * f
HEIGHT: int = 1080 * f

# --- Farben (RGBA) ---
BORDER_COLOR = (255, 255, 255, 255)      # Rand/Crash
FINISH_LINE_COLOR = (237, 28, 36, 255)   # Ziellinie (rot)
OUT_BORDER_COLOR = (0, 0, 0, 255)

# --- Sensorik ---
RADAR_SWEEP_DEG: int = 60                # ±60°
MAX_RADAR_LEN_RATIO: float = 130 / 1900  # max_len_px = WIDTH * Ratio

# --- Fahrzeugmaße in Pixel (werden später gesetzt/initialisiert) ---
CAR_SIZE_X: float = 0.0
CAR_SIZE_Y: float = 0.0
CAR_cover_size: int = 0
CAR_Radstand: float = 0.0
CAR_Spurweite: float = 0.0

# Optional: Hilfs-Init, falls du später echte Pixelwerte aus cm berechnen willst
def init_pixels(real_to_sim):
    global CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size, CAR_Radstand, CAR_Spurweite
    CAR_SIZE_X = float(real_to_sim(40.0))
    CAR_SIZE_Y = float(real_to_sim(20.0))
    CAR_cover_size = int(max(CAR_SIZE_X, CAR_SIZE_Y))
    CAR_Radstand = float(real_to_sim(25.0))
    CAR_Spurweite = float(real_to_sim(10.0))

__all__ = [
    "f","WIDTH","HEIGHT",
    "BORDER_COLOR","FINISH_LINE_COLOR","OUT_BORDER_COLOR",
    "RADAR_SWEEP_DEG","MAX_RADAR_LEN_RATIO",
    "CAR_SIZE_X","CAR_SIZE_Y","CAR_cover_size","CAR_Radstand","CAR_Spurweite",
    "init_pixels",
]
