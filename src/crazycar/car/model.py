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

# --- Reexports für Altcode (simulation.py etc.) ---
from .constants import f as f, WIDTH as WIDTH, HEIGHT as HEIGHT   # noqa: F401
from .units import sim_to_real as sim_to_real                      # noqa: F401

# Abgeleitete Pixelwerte initialisieren
init_pixels(real_to_sim)


class Car:
    def __init__(self, position, carangle, power, speed_set, radars, bit_volt_wert_list, distance, time):
        # Sprite laden
        self.sprite = load_car_sprite(CAR_cover_size)
        self.rotated_sprite = self.sprite

        # Zustand
        self.position = position
        self.center = [self.position[0] + CAR_cover_size / 2, self.position[1] + CAR_cover_size / 2]
        self.corners = []
        self.left_rad = []
        self.right_rad = []

        self.fwert = power
        self.swert = 0
        self.sollspeed = self.soll_speed(power)  # Wrapper ruft dynamics.soll_speed
        self.speed = 0
        self.speed_set = speed_set
        self.power = power
        self.radangle = 0
        self.carangle = carangle

        self.radars = radars
        self.radar_angle = 60
        self.radar_dist = []
        self.bit_volt_wert_list = bit_volt_wert_list
        self.drawing_radars = []

        self.alive = True
        self.speed_slowed = False
        self.angle_enable = True
        self.radars_enable = True
        self.drawradar_enable = True
        self.regelung_enable = True

        self.distance = distance
        self.anlog_dist = []
        self.time = time
        self.start_time = 0
        self.round_time = 0
        self.finished = False
        self.maxpower = 100

    # --- Kompatibilitäts-Wrapper (API beibehalten) ---

    def soll_speed(self, power: float) -> float:
        """Alter Methodenname -> delegiert auf dynamics.soll_speed."""
        return _soll_speed(power)

    def Geschwindigkeit(self, power: float) -> float:
        """Alter Methodenname -> delegiert auf dynamics.step_speed mit aktuellem Zustand."""
        return step_speed(self.speed, power, self.radangle)

    def rotate_center(self, image, angle):
        """Behalte alte Signatur, delegiere auf rendering.rotate_center."""
        return rotate_center(image, angle)

    def draw(self, screen):
        """Behalte alte Signatur, delegiere auf rendering.draw_* (Liste -> Tupel)."""
        draw_car(screen, self.rotated_sprite, tuple(self.position))
        self.draw_radar(screen)

    def draw_track(self, screen):
        """Behalte alte Signatur, delegiere auf rendering.draw_track (Listen -> Tupel)."""
        draw_track(
            screen,
            tuple(self.left_rad),
            tuple(self.right_rad),
            [tuple(p) for p in self.corners],
        )

    def draw_radar(self, screen):
        """Behalte alte Signatur, delegiere auf rendering.draw_radar (Liste -> Tupel)."""
        draw_radar(screen, tuple(self.center), self.radars, self.drawradar_enable)

    def delay_ms(self, milliseconds: int):
        """Behalte alte Signatur, delegiere auf timeutil.delay_ms."""
        delay_ms(milliseconds)

    # --- Deine weiteren Methoden (update, check_collision, check_radar, ...) hier anhängen ---
    # def update(...): ...
    # def check_collision(...): ...
    # def check_radar(...): ...
    # etc.


# __all__ MUSS ans Ende (nach der Klassendefinition)
__all__ = ["Car", "f", "WIDTH", "HEIGHT", "sim_to_real"]
