# crazycar/car/model.py
import math

from .constants import (
    init_pixels, f, WIDTH, HEIGHT,
    CAR_cover_size, CAR_Radstand, CAR_Spurweite,
    CAR_SIZE_X, CAR_SIZE_Y, BORDER_COLOR, FINISH_LINE_COLOR
)
from .units import sim_to_real, real_to_sim
from .rendering import load_car_sprite, rotate_center, draw_car, draw_radar, draw_track
from .geometry import compute_corners, compute_wheels
from .kinematics import steer_step
from .dynamics import soll_speed as _soll_speed, step_speed
from .sensors import collect_radars, distances as radars_distances, linearize_DA
from .collision import collision_step
from .actuation import servo_to_angle, clip_steer, apply_power
from .timeutil import delay_ms

# --- Reexports für Abwärtskompatibilität (wichtig für simulation.py) ---
# Dadurch bleiben alte Imports aus model.py gültig.
from .constants import f as f, WIDTH as WIDTH, HEIGHT as HEIGHT   # noqa: F401  (re-export)
from .units import sim_to_real as sim_to_real                      # noqa: F401  (re-export)

__all__ = ["Car", "f", "WIDTH", "HEIGHT", "sim_to_real"]

# einmalig abgeleitete Pixelwerte berechnen
init_pixels(real_to_sim)
