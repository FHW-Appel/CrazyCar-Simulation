# crazycar/car/model.py
from __future__ import annotations
import os
import math
import logging

from . import constants as C
from .constants import (
    init_pixels, f, WIDTH, HEIGHT,
    BORDER_COLOR, FINISH_LINE_COLOR
)
from .units import sim_to_real, real_to_sim
from .rendering import load_car_sprite, rotate_center, draw_car, draw_radar, draw_track
from .geometry import compute_corners, compute_wheels
from .kinematics import steer_step
from .dynamics import soll_speed as _soll_speed, step_speed
from .sensors import distances as radars_distances, linearize_DA, cast_radar
from .collision import collision_step
from .actuation import apply_power
from .timeutil import delay_ms

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.car")

# ------------------------------------------------------------
# Abgeleitete Pixelwerte initialisieren (nachdem real_to_sim importiert ist!)
# ------------------------------------------------------------
init_pixels(real_to_sim)

# Falls die Konvertierung schief ging, Defaults im constants-Modul setzen
if C.CAR_cover_size <= 0 or C.CAR_SIZE_X <= 0 or C.CAR_SIZE_Y <= 0 or C.CAR_Radstand <= 0 or C.CAR_Spurweite <= 0:
    log.error("Geometrie unplausibel (0-Werte). Fallback auf safe Defaults.")
    if C.CAR_SIZE_X <= 0 or C.CAR_SIZE_Y <= 0:
        C.CAR_SIZE_X, C.CAR_SIZE_Y = 32.0, 16.0
        C.CAR_cover_size = int(max(C.CAR_SIZE_X, C.CAR_SIZE_Y))
    if C.CAR_Radstand <= 0 or C.CAR_Spurweite <= 0:
        C.CAR_Radstand, C.CAR_Spurweite = 25.0, 10.0

# *** WICHTIG: Lokale Bindungen aus dem aktuellen constants-Zustand herstellen ***
CAR_SIZE_X: float   = float(C.CAR_SIZE_X)
CAR_SIZE_Y: float   = float(C.CAR_SIZE_Y)
# min. 16 px, damit Sprite nie (0,0) wird und Center korrekt berechnet wird
CAR_cover_size: int = max(int(C.CAR_cover_size), 16)
CAR_Radstand: float = float(C.CAR_Radstand)
CAR_Spurweite: float = float(C.CAR_Spurweite)

if os.getenv("CRAZYCAR_DEBUG") == "1":
    log.info(
        "geom: WIDTH=%d HEIGHT=%d  L=%.2fpx W=%.2fpx  size_x=%.2f size_y=%.2f cover=%dpx",
        WIDTH, HEIGHT, CAR_Radstand, CAR_Spurweite, CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size
    )


class Car:
    def __init__(self, position, carangle, power, speed_set, radars, bit_volt_wert_list, distance, time):
        # Instanzweite Cover-Size (robust)
        self.cover_size = CAR_cover_size

        # Sprite laden (rendering.py clamped zusätzlich)
        self.sprite = load_car_sprite(self.cover_size)
        self.rotated_sprite = self.sprite

        self.position = position
        self.center = [self.position[0] + self.cover_size / 2, self.position[1] + self.cover_size / 2]
        self.corners = []
        self.left_rad = []
        self.right_rad = []

        self.fwert = power
        self.swert = 0
        self.sollspeed = self.soll_speed(power)
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

        log.info(
            "Car init: pos=(%.1f,%.1f) angle=%.1f power=%.1f cover=%dpx",
            self.position[0], self.position[1], self.carangle, self.power, self.cover_size
        )

    # Wrappers
    def soll_speed(self, power: float) -> float:
        return _soll_speed(power)

    def Geschwindigkeit(self, power: float) -> float:
        return step_speed(self.speed, power, self.radangle)

    def rotate_center(self, image, angle):  # API-Kompat
        return rotate_center(image, angle)

    def draw(self, screen):
        draw_car(screen, self.rotated_sprite, tuple(self.position))
        self.draw_radar(screen)

    def draw_track(self, screen):
        draw_track(screen, tuple(self.left_rad), tuple(self.right_rad), [tuple(p) for p in self.corners])

    def draw_radar(self, screen):
        draw_radar(screen, tuple(self.center), self.radars, self.drawradar_enable)

    def delay_ms(self, milliseconds: int):
        delay_ms(milliseconds)

    def set_position(self, position):  # Altcode-Kompat
        self.position = position

    def Lenkeinschlagsänderung(self):
        old = self.carangle
        self.carangle = steer_step(
            carangle_deg=self.carangle,
            radangle_deg=self.radangle,
            speed_px=self.speed,
            radstand_px=CAR_Radstand,
            spurweite_px=CAR_Spurweite,
        )
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("steer_step: rad=%.2f° speed=%.3f angle %.4f→%.4f",
                      self.radangle, self.speed, old, self.carangle)
        return self.carangle

    def check_radar(self, degree, game_map):
        color_at = lambda pos: game_map.get_at((int(pos[0]), int(pos[1])))
        max_len_px = float(WIDTH) * 130.0 / 1900.0
        (x, y), dist = cast_radar(
            center=tuple(self.center),
            carangle_deg=self.carangle,
            degree_offset=int(degree),
            color_at=color_at,
            max_len_px=max_len_px,
            border_color=BORDER_COLOR,
        )
        self.radars.append([(int(x), int(y)), int(dist)])

    def get_radars_dist(self):
        self.radar_dist = radars_distances(self.radars)
        return self.radar_dist

    def linearisierungDA(self):
        dist_px = self.get_radars_dist()
        dist_cm = [sim_to_real(d) for d in dist_px]
        return linearize_DA(dist_cm)

    def check_radars_enable(self, sensor_status: int):
        on = (sensor_status == 0)
        self.radars_enable = on
        self.angle_enable = on
        self.drawradar_enable = on

    def check_collision(self, game_map, collision_status: int):
        color_at = lambda pos: game_map.get_at((int(pos[0]), int(pos[1])))

        def _on_lap(rt: float):
            if self.round_time == 0:
                self.round_time = rt

        new_speed, new_angle, alive, finished, round_time, flags = collision_step(
            corners=[tuple(p) for p in self.corners],
            color_at=color_at,
            collision_status=int(collision_status),
            speed=float(self.speed),
            carangle=float(self.carangle),
            time_now=float(self.time),
            border_color=BORDER_COLOR,
            finish_color=FINISH_LINE_COLOR,
            on_lap_time=_on_lap,
        )
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("collision: speed %.3f→%.3f angle %.4f→%.4f flags=%s",
                      self.speed, new_speed, self.carangle, new_angle, flags)

        self.speed = new_speed
        self.carangle = new_angle
        self.alive = alive
        self.finished = finished
        if round_time and self.round_time == 0:
            self.round_time = round_time

        dx, dy = flags.get("pos_delta", (0.0, 0.0))
        self.position[0] += dx
        self.position[1] += dy
        if flags.get("disable_control", False):
            self.regelung_enable = False
            log.warning("Regelung deaktiviert (collision flag).")

    def update(self, game_map, drawtracks: bool, sensor_status: int, collision_status: int):
        # einmalige Geometrie-Logs
        if not hasattr(self, "_once_dims_logged"):
            log.debug("ONCE: size_x=%.2f size_y=%.2f cover=%d radstand=%.2f spurweite=%.2f",
                      CAR_SIZE_X, CAR_SIZE_Y, self.cover_size, CAR_Radstand, CAR_Spurweite)
            self._once_dims_logged = True

        # Zeit/Distanz
        self.distance += self.speed
        self.time += 0.01

        # Sprite rotieren
        self.rotated_sprite = rotate_center(self.sprite, self.carangle)

        # Lenkung
        if getattr(self, "radangle", 0) != 0:
            self.carangle = self.Lenkeinschlagsänderung()

        # Translation
        old_pos = (self.position[0], self.position[1])
        self.position[0] += math.cos(math.radians(360 - self.carangle)) * self.speed
        self.position[1] += math.sin(math.radians(360 - self.carangle)) * self.speed

        # Begrenzen
        self.position[0] = max(self.position[0], 10 * f)
        self.position[0] = min(self.position[0], WIDTH - 10 * f)
        self.position[1] = max(self.position[1], 10 * f)
        self.position[1] = min(self.position[1], HEIGHT - 10 * f)

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug(
                "tick: t=%.2f pos (%.3f,%.3f) -> (%.3f,%.3f) angle=%.4f rad=%.2f speed=%.3f power=%.2f",
                self.time, old_pos[0], old_pos[1], self.position[0], self.position[1],
                self.carangle, self.radangle, self.speed, self.power
            )

        # Center (mit Instanz-cover_size!)
        self.center = [int(self.position[0]) + self.cover_size / 2, int(self.position[1]) + self.cover_size / 2]
        self.set_position(self.position)

        # Ecken/Räder
        half_len = 0.5 * CAR_SIZE_X
        half_wid = 0.5 * CAR_SIZE_Y
        self.corners = compute_corners(tuple(self.center), self.carangle, half_len, half_wid)
        diag_minus = (half_len**2 + half_wid**2) ** 0.5 - 6
        self.left_rad, self.right_rad = compute_wheels(tuple(self.center), self.carangle, diag_minus)

        # Kollision
        self.check_collision(game_map, collision_status)

        # Track?
        if drawtracks:
            self.draw_track(game_map)

        # Radare
        self.radars.clear()
        self.check_radars_enable(sensor_status)
        if self.radars_enable:
            color_at = lambda pos: game_map.get_at((int(pos[0]), int(pos[1])))
            max_len_px = float(WIDTH) * 130.0 / 1900.0
            for deg in (-self.radar_angle, 0, self.radar_angle):
                (x, y), dist = cast_radar(
                    center=tuple(self.center),
                    carangle_deg=self.carangle,
                    degree_offset=int(deg),
                    color_at=color_at,
                    max_len_px=max_len_px,
                    border_color=BORDER_COLOR,
                )
                self.radars.append([(int(x), int(y)), int(dist)])

            self.radar_dist = self.get_radars_dist()
            self.bit_volt_wert_list = self.linearisierungDA()
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug("radars: dist(px)=%s bit/volt=%s",
                          self.radar_dist, self.bit_volt_wert_list)

    def getmotorleistung(self, fwert):
        def _speed_fn(pwr: float) -> float:
            new_speed = step_speed(self.speed, pwr, self.radangle)
            self.speed = new_speed
            return new_speed

        new_power, _ = apply_power(
            fwert=float(fwert),
            current_power=float(self.power),
            current_speed_px=float(self.speed),
            maxpower=float(self.maxpower),
            speed_fn=_speed_fn,
            delay_fn=delay_ms,
        )
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug("apply_power: fwert=%.1f power %.1f→%.1f speed=%.3f",
                      fwert, self.power, new_power, self.speed)
        self.power = new_power

    def is_alive(self):       return self.alive
    def get_reward(self):     return self.distance / (CAR_SIZE_X / 2)
    def get_round_time(self): return self.round_time
    def get_finished(self):   return self.finished


def set_position(obj, position):
    obj.set_position(position)


__all__ = ["Car", "f", "WIDTH", "HEIGHT", "sim_to_real"]
