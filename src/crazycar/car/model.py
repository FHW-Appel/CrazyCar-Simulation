"""Vehicle Model - Main Interface (Car Class).

This module implements the central Car class that orchestrates all vehicle
components: physics, sensors, collision and rendering.

Class:
- Car: Complete vehicle model with all subsystems

Main Components:
1. **Geometry**: Position, corners, wheels (geometry.py)
2. **Physics**: Kinematics (steer_step), Dynamics (step_speed)
3. **Sensors**: Radar casting (sensors.py)
4. **Collision**: Wall/finish line detection (collision.py)
5. **Rendering**: Sprite rotation, drawing (rendering.py)
6. **Actuation**: Power → Speed mapping (actuation.py)

API Overview:
- __init__(): Initialization with position, angle, etc.
- update(): Main loop (motion, collision, sensors)
- getmotorleistung(): Power update (external control)
- draw(): Rendering to pygame.Surface
- check_collision(): Collision check against map
- check_radar(): Single radar cast

Legacy Compatibility:
- self.fwert, self.swert: DEPRECATED (use self.power, self.radangle)
- Geschwindigkeit(), Lenkeinschlagsänderung(): Legacy names

Constants:
- MIN_SPRITE_SIZE: 16px (minimum sprite size)
- RADAR_DEFAULT_SWEEP: 60° (default radar sweep angle)
- MAX_POWER_DEFAULT: 100 (maximum motor power)

See Also:
- constants.py: Global configuration (dimensions, colors)
- state.py: CarState (alternative, modern data structure)
"""
# crazycar/car/model.py
from __future__ import annotations
import os
import math
import logging

"""Der Orchestrator und die eigentliche Car-Klasse. 
    Car.update(surface, drawtracks, sensors_on, collision_mode) holt 
    sich Sensordaten, berechnet Lenk-/Fahrdynamik, prüft Kollisionen 
    und aktualisiert Position, Car.draw(screen) rendert Sprite, Sensoren 
    und optional Spuren. Hilfsfunktionen wie is_alive(), get_round_time(), 
    Geschwindigkeit(power) (vereinfachte Längsdynamik), sowie Properties für Distanz, Zeiten, 
    aktuelle Radar-Listen und Regler-I/Os binden die oben genannten Module zusammen."""

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

# Initialize derived pixel values (after real_to_sim import)
init_pixels(real_to_sim)

# Set defaults in constants module if conversion failed
if C.CAR_cover_size <= 0 or C.CAR_SIZE_X <= 0 or C.CAR_SIZE_Y <= 0 or C.CAR_Radstand <= 0 or C.CAR_Spurweite <= 0:
    log.error("Implausible geometry (zero values). Fallback to safe defaults.")
    if C.CAR_SIZE_X <= 0 or C.CAR_SIZE_Y <= 0:
        C.CAR_SIZE_X, C.CAR_SIZE_Y = 32.0, 16.0  # Fallback dimensions [pixels]: length x width
        C.CAR_cover_size = int(max(C.CAR_SIZE_X, C.CAR_SIZE_Y))
    if C.CAR_Radstand <= 0 or C.CAR_Spurweite <= 0:
        C.CAR_Radstand, C.CAR_Spurweite = 25.0, 10.0  # Fallback [pixels]: wheelbase x track width

# *** IMPORTANT: Create local bindings from current constants state ***
CAR_SIZE_X: float   = float(C.CAR_SIZE_X)
CAR_SIZE_Y: float   = float(C.CAR_SIZE_Y)
# Minimum sprite size to avoid (0,0) dimensions
MIN_SPRITE_SIZE = 16  # Pixels
CAR_cover_size: int = max(int(C.CAR_cover_size), MIN_SPRITE_SIZE)
CAR_Radstand: float = float(C.CAR_Radstand)
CAR_Spurweite: float = float(C.CAR_Spurweite)

if os.getenv("CRAZYCAR_DEBUG") == "1":
    log.info(
        "geom: WIDTH=%d HEIGHT=%d  L=%.2fpx W=%.2fpx  size_x=%.2f size_y=%.2f cover=%dpx",
        WIDTH, HEIGHT, CAR_Radstand, CAR_Spurweite, CAR_SIZE_X, CAR_SIZE_Y, CAR_cover_size
    )


class Car:
    """Main vehicle model integrating physics, rendering, sensors and control.
    
    Encapsulates all car state (position, angle, speed, sensors) and orchestrates
    updates via modular components (kinematics, dynamics, collision, rendering).
    Provides both simulation (step_*) and legacy API compatibility methods.
    
    Attributes:
        position: Top-left corner [x, y] in pixels
        center: Center point [x, y] in pixels
        carangle: Orientation in degrees (0° = right, 90° = down)
        speed: Current speed in pixels per frame
        alive: Whether car is still active (not crashed)
        radars: Sensor readings [(contact_point, distance), ...]
        
    Note:
        Uses global CAR_cover_size, CAR_Radstand, CAR_Spurweite constants.
    """
    def __init__(self, position, carangle, power, speed_set, radars, bit_volt_wert_list, distance, time):
        # Sprite size (instance-wide, robust against changes)
        self.cover_size = CAR_cover_size

        # Load car sprite and initial rotation
        self.sprite = load_car_sprite(self.cover_size)
        self.rotated_sprite = self.sprite

        # Position and geometry
        self.position = position
        self.center = [self.position[0] + self.cover_size / 2, self.position[1] + self.cover_size / 2]
        self.corners = []  # Car corners (set by geometry.compute_corners)
        self.left_rad = []   # Left track (tracking)
        self.right_rad = []  # Right track (tracking)

        # Drive and steering
        # DEPRECATED: Legacy attributes for compatibility with old NEAT controllers (pre v2.0)
        # TODO: Remove in v2.0 when all controllers migrated to self.power/self.radangle
        self.fwert = power  # DEPRECATED: Use self.power instead (forward power 0-100)
        self.swert = 0      # DEPRECATED: Use self.radangle instead (steering angle in °)
        
        self.sollspeed = self.soll_speed(power)  # Target speed [px/frame]
        self.speed = 0  # Current speed [px/frame]
        self.speed_set = speed_set  # Speed setpoint (configurable)
        self.power = power  # Current motor power (0-100)
        self.radangle = 0   # Front wheel steering angle [°] (positive=right)
        self.carangle = carangle  # Vehicle orientation [°] (0=right, 90=down)

        # Sensors (Radars)
        self.radars = radars
        RADAR_DEFAULT_SWEEP = 60  # Default sweep ±60° (from constants.RADAR_SWEEP_DEG)
        self.radar_angle = RADAR_DEFAULT_SWEEP
        self.radar_dist = []
        self.bit_volt_wert_list = bit_volt_wert_list  # ADC values (Analog→Digital)
        self.drawing_radars = []

        # State flags
        self.alive = True
        self.speed_slowed = False  # Was speed reduced by collision?
        self.angle_enable = True
        self.radars_enable = True
        self.drawradar_enable = True
        self.regelung_enable = True  # Controller active?

        # Performance tracking
        self.distance = distance  # Driven distance in pixels
        self.anlog_dist = []
        self.time = time
        self.start_time = 0
        self.round_time = 0
        self.finished = False
        MAX_POWER_DEFAULT = 100  # Maximum power (0-100)
        self.maxpower = MAX_POWER_DEFAULT

        log.info(
            "Car init: pos=(%.1f,%.1f) angle=%.1f power=%.1f cover=%dpx",
            self.position[0], self.position[1], self.carangle, self.power, self.cover_size
        )

    # Wrapper methods for external modules
    def soll_speed(self, power: float) -> float:
        """Compute target speed for given power level."""
        return _soll_speed(power)

    def Geschwindigkeit(self, power: float) -> float:
        """Update current speed based on power and steering angle."""
        return step_speed(self.speed, power, self.radangle)

    def rotate_center(self, image, angle):  # Legacy API compatibility
        """Rotate image around its center (legacy wrapper)."""
        return rotate_center(image, angle)

    def draw(self, screen):
        """Draw car sprite and radar overlay on screen."""
        draw_car(screen, self.rotated_sprite, tuple(self.position))
        self.draw_radar(screen)

    def draw_track(self, screen):
        """Draw driving track (left/right traces and corner markers)."""
        draw_track(screen, tuple(self.left_rad), tuple(self.right_rad), [tuple(p) for p in self.corners])

    def draw_radar(self, screen):
        """Draw radar sensor visualization."""
        draw_radar(screen, tuple(self.center), self.radars, self.drawradar_enable)

    def delay_ms(self, milliseconds: int):
        """Sleep for given milliseconds (for frame timing)."""
        delay_ms(milliseconds)

    def set_position(self, position):  # Legacy code compatibility
        """Update car position (legacy method)."""
        self.position = position

    def Lenkeinschlagsänderung(self):
        """Update car angle based on steering and speed (legacy name).
        
        Returns:
            Float: New car angle in degrees.
        """
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
        """Cast single radar beam at given angle offset.
        
        Args:
            degree (float): Angle offset from car direction (degrees)
            game_map (pygame.Surface): Map surface for color lookups
            
        Note:
            Appends result to self.radars list.
        """
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
        """Extract distances from radar results.
        
        Returns:
            List[float]: Distances in pixels for each radar beam
        """
        self.radar_dist = radars_distances(self.radars)
        return self.radar_dist

    def linearisierungDA(self):
        """Convert radar distances to ADC values (Digital-Analog linearization).
        
        Converts pixel distances to centimeters, then applies sensor
        linearization curve to simulate analog sensor characteristics.
        
        Returns:
            List[float]: Linearized ADC values (bit/volt)
        """
        dist_px = self.get_radars_dist()
        dist_cm = [sim_to_real(d) for d in dist_px]
        return linearize_DA(dist_cm)

    def check_radars_enable(self, sensor_status: int):
        """Enable/disable radar sensors based on UI toggle.
        
        Args:
            sensor_status (int): 0 = sensors ON, 1 = sensors OFF
            
        Note:
            Updates self.radars_enable, self.angle_enable, self.drawradar_enable.
        """
        on = (sensor_status == 0)
        self.radars_enable = on
        self.angle_enable = on
        self.drawradar_enable = on

    def check_collision(self, game_map, collision_status: int):
        """Check for wall/finish-line collision and apply physics.
        
        Args:
            game_map (pygame.Surface): Map surface for color lookups
            collision_status (int): Collision mode (0=rebound, 1=stop, 2=remove)
            
        Note:
            Updates self.speed, self.carangle, self.alive, self.finished,
            self.round_time, self.position, self.regelung_enable.
        """
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
            log.warning("Controller disabled (collision flag).")

    def update(self, game_map, drawtracks: bool, sensor_status: int, collision_status: int):
        """Main update loop - physics, collision, sensors.
        
        Executes full simulation step:
        1. Time/distance tracking
        2. Sprite rotation
        3. Steering (if radangle != 0)
        4. Translation (position update)
        5. Boundary clamping
        6. Geometry update (corners, wheels)
        7. Collision detection
        8. Radar sensors (if enabled)
        
        Args:
            game_map (pygame.Surface): Map surface for collision/radar
            drawtracks (bool): Whether to draw driving traces
            sensor_status (int): Sensor enable/disable (0=ON, 1=OFF)
            collision_status (int): Collision mode (0=rebound, 1=stop, 2=remove)
            
        Note:
            Updates all car state (position, speed, sensors, etc.).
        """
        # One-time geometry logging
        if not hasattr(self, "_once_dims_logged"):
            log.debug("ONCE: size_x=%.2f size_y=%.2f cover=%d radstand=%.2f spurweite=%.2f",
                      CAR_SIZE_X, CAR_SIZE_Y, self.cover_size, CAR_Radstand, CAR_Spurweite)
            self._once_dims_logged = True

        # Time/distance tracking
        self.distance += self.speed
        self.time += 0.01

        # Rotate sprite
        self.rotated_sprite = rotate_center(self.sprite, self.carangle)

        # Steering
        if getattr(self, "radangle", 0) != 0:
            self.carangle = self.Lenkeinschlagsänderung()

        # Translation
        old_pos = (self.position[0], self.position[1])
        self.position[0] += math.cos(math.radians(360 - self.carangle)) * self.speed
        self.position[1] += math.sin(math.radians(360 - self.carangle)) * self.speed

        # Clamp to boundaries
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

        # Update center point (using instance cover_size)
        self.center = [int(self.position[0]) + self.cover_size / 2, int(self.position[1]) + self.cover_size / 2]
        self.set_position(self.position)

        # Compute corners and wheels
        half_len = 0.5 * CAR_SIZE_X
        half_wid = 0.5 * CAR_SIZE_Y
        self.corners = compute_corners(tuple(self.center), self.carangle, half_len, half_wid)
        diag_minus = (half_len**2 + half_wid**2) ** 0.5 - 6
        self.left_rad, self.right_rad = compute_wheels(tuple(self.center), self.carangle, diag_minus)

        # Collision detection
        self.check_collision(game_map, collision_status)

        # Draw track traces if enabled
        if drawtracks:
            self.draw_track(game_map)

        # Radar sensors
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
        """Apply power input to motor (external control interface).
        
        Delegates to actuation.apply_power() which handles ramping,
        delays, and speed updates.
        
        Args:
            fwert (float): Target forward power (0-100)
            
        Note:
            Updates self.power and self.speed.
        """
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
    """Legacy helper - Set car position.
    
    Args:
        obj: Car instance
        position: [x, y] coordinates
        
    Deprecated:
        Use car.set_position(position) directly
    """
    obj.set_position(position)


__all__ = ["Car", "f", "WIDTH", "HEIGHT", "sim_to_real"]
