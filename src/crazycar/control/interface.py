"""Control Interface - NEAT genome to car control bridge.

Responsibilities:
- Define abstract control interface for car actuation
- Provide Python and C implementation adapters
- Manage NEAT neural network genomes
- Import and validate native C extension (carsim_native)
- Handle car sensor inputs and control outputs

Public API:
- class ControllerInterface (ABC):
      Abstract base for all controllers
      feed_sensors(car: Car) -> None
      compute() -> tuple[float, float]  # (power, steering)
      
- class PythonController(ControllerInterface):
      NEAT genome-based controller
      Uses feed-forward neural network for control decisions
      
- class CController(ControllerInterface):
      Native C-based controller via CFFI
      Calls regelungtechnik() from myFunktions.c
      
- class Interface:
      Main API for creating controllers
      spawn(car: Car, genome, config, use_python: bool) -> ControllerInterface

Usage:
    # Create Python controller with NEAT genome
    iface = Interface()
    controller = iface.spawn(car, genome, neat_config, use_python=True)
    controller.feed_sensors(car)
    power, steer = controller.compute()
    
    # Create C controller
    c_controller = iface.spawn(car, None, None, use_python=False)
    c_controller.feed_sensors(car)
    power, steer = c_controller.compute()  # Calls C code

Notes:
- Ensures build/_cffi on sys.path for native imports
- Validates C extension symbols at import
- Required symbols: regelungtechnik, getfwert, getswert, sensor getters
- Python mode uses NEAT-Python for evolutionary learning
- C mode tests native implementation (myFunktions.c)
"""
# crazycar/control/interface.py
from __future__ import annotations
import os
import sys
import math
import logging
import importlib
from importlib import invalidate_caches
from abc import ABC, abstractmethod
from typing import List, Any

from crazycar.car import model
from crazycar.car.actuation import servo_to_angle, clip_steer, apply_power
import time  # For delay_fn

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
log = logging.getLogger("crazycar.control.interface")

# --------------------------------------------------------------------
# Ensure build/_cffi is importable (also in child)
# --------------------------------------------------------------------
_build_dir: str | None = None
try:
    from crazycar.interop.build_tools import ensure_build_on_path
    _build_dir = ensure_build_on_path()
    if _build_dir and _build_dir not in sys.path:
        sys.path.insert(0, _build_dir)
except Exception as _e:
    log.debug("ensure_build_on_path failed (ok, will try without): %r", _e)

# --------------------------------------------------------------------
# More robust import / symbol self-test for native module
# --------------------------------------------------------------------
REQUIRED_ANY_POWER = ("getfahr", "fahr")
REQUIRED_ANY_STEER = ("getservo", "servo")
REQUIRED_ALWAYS = (
    "regelungtechnik", "getfwert", "getswert",
    "getabstandvorne", "getabstandrechts", "getabstandlinks",
)


def _prefer_build_import() -> tuple[bool, Any, Any, str]:
    """
    Import crazycar.carsim_native preferably from build/_cffi and verify
    required symbols. Returns: (ok, ffi, lib, mod_file)
    """
    build_dir = None
    try:
        from crazycar.interop.build_tools import ensure_build_on_path
        build_dir = ensure_build_on_path()
    except Exception:
        build_dir = None

    # Clean import state.
    sys.modules.pop("crazycar.carsim_native", None)
    invalidate_caches()
    if build_dir and build_dir not in sys.path:
        sys.path.insert(0, build_dir)

    try:
        mod = importlib.import_module("crazycar.carsim_native")
    except Exception:
        return False, None, None, ""

    mod_file = getattr(mod, "__file__", "") or ""
    ffi_local, lib_local = getattr(mod, "ffi", None), getattr(mod, "lib", None)

    def _has_any(names: tuple[str, ...]) -> bool:
        return lib_local is not None and any(hasattr(lib_local, n) for n in names)

    required_ok = (
        lib_local is not None
        and _has_any(REQUIRED_ANY_POWER)
        and _has_any(REQUIRED_ANY_STEER)
        and all(hasattr(lib_local, n) for n in REQUIRED_ALWAYS)
    )

    return bool(required_ok), ffi_local, lib_local, mod_file

# --------------------------------------------------------------------
# Optional: Load native C module (fallback to Python controller)
# Force loading from build/_cffi if possible.
# --------------------------------------------------------------------
ffi = None
lib = None
_NATIVE_OK = False
try:
    ok, ffi, lib, mf = _prefer_build_import()
    _NATIVE_OK = bool(ok)
    if _NATIVE_OK:
        log.info("Native module loaded: %s (C controller available).", mf)
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            have = lambda n: hasattr(lib, n)
            log.debug(
                "carsim_native symbols: getfahr=%s, fahr=%s, getservo=%s, servo=%s, "
                "getfwert=%s, getswert=%s, regelungtechnik=%s",
                have("getfahr"), have("fahr"), have("getservo"), have("servo"),
                have("getfwert"), have("getswert"), have("regelungtechnik")
            )
    else:
        log.error("Native module loaded (%s), but symbols missing → fallback to Python controller.", mf)
except Exception as e:
    log.warning("No native module available, using Python controller. Reason: %r", e)

# Optional: hard requirement that C controller must be present
if os.getenv("CRAZYCAR_FORCE_C") == "1" and not _NATIVE_OK:
    raise RuntimeError("CRAZYCAR_FORCE_C=1 set, but C controller not available or incomplete.")

# ------------------------------------------------------------
# Setter resolver (resolve once, then call directly)
# ------------------------------------------------------------
_set_power = None  # type: ignore[assignment]
_set_steer = None  # type: ignore[assignment]
if _NATIVE_OK and lib is not None:
    if hasattr(lib, "getfahr"):
        _set_power = getattr(lib, "getfahr")
    elif hasattr(lib, "fahr"):
        _set_power = getattr(lib, "fahr")

    if hasattr(lib, "getservo"):
        _set_steer = getattr(lib, "getservo")
    elif hasattr(lib, "servo"):
        _set_steer = getattr(lib, "servo")

    if (_set_power is None) or (_set_steer is None):
        # Don't abort hard – Python controller takes over automatically below
        missing = []
        if _set_power is None:
            missing.append("getfahr/fahr")
        if _set_steer is None:
            missing.append("getservo/servo")
        log.error("C controller: missing setters (%s) – fallback to Python controller.", ", ".join(missing))
        _NATIVE_OK = False

# --------------------------------------------------------------------
# Sim/control parameters
# --------------------------------------------------------------------
WIDTH = model.WIDTH
HEIGHT = model.HEIGHT

# Optimizer can override these values (via file edit)
k1 = 1.1
k2 = 1.1
k3 = 1.1
kp1 = 1.1
kp2 = 1.1


class MyInterface(ABC):
    """Abstract base class defining controller interface contract.
    
    Defines required methods for both C and Python controller implementations.
    Ensures consistent API across different controller backends.
    """
    @staticmethod
    @abstractmethod
    def regelungtechnik_c(cars: List[Any]) -> None: ...
    @staticmethod
    @abstractmethod
    def regelungtechnik_python(cars: List[Any]) -> None: ...


class Interface(MyInterface):
    """Main controller interface with C/Python fallback logic.
    
    Provides unified API for vehicle control, automatically selecting
    between native C controller (DLL) and Python fallback implementation.
    Handles sensor data conversion, output application, and UI helpers.
    """
    # ------------------------------------------------------------
    # Helper function: Apply controller outputs to vehicle
    # ------------------------------------------------------------
    @staticmethod
    def _apply_outputs_to_car(car, fwert: float, swert: float) -> None:
        """Apply actuation outputs and log results."""
        # Steering.
        clipped = clip_steer(swert)
        radangle = -servo_to_angle(clipped)
        car.radangle = radangle
        # Power mapping with deadzone/min-start logic
        # Configuration: maxpower=100, delay_fn noop (no real wait in sim loop)
        try:
            maxpower = 100.0
            current_speed = getattr(car, "speed", 0.0)
            new_power, new_speed = apply_power(
                fwert=fwert,
                current_power=getattr(car, "power", 0.0),
                current_speed_px=current_speed,
                maxpower=maxpower,
                speed_fn=car.Geschwindigkeit,
                delay_fn=lambda ms: None,  # No delay in simulation loop
            )

            # **Set state** – first power, then synchronize legacy paths
            car.power = new_power
            # Maintain legacy side effects:
            try:
                car.getmotorleistung(new_power)
            except Exception:
                # If getmotorleistung is not a setter, no problem.
                pass

            # Set speed consistently.
            try:
                car.speed = car.Geschwindigkeit(car.power)
            except Exception:
                car.speed = new_speed

            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "ACTUATE_MAP: fwert=%5.1f -> power=%6.2f speed=%7.3f (radangle=%6.2f°)",
                    fwert, car.power, car.speed, radangle
                )

        except Exception as _e:
            # Fallback: Leave old behavior unchanged.
            try:
                car.getmotorleistung(fwert)
            except Exception:
                pass
            try:
                car.speed = car.Geschwindigkeit(car.power)
            except Exception:
                # Leave speed as-is if even this fails.
                pass
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "ACTUATE_FALLBACK: fwert=%5.1f radangle=%6.2f° power=%6.2f speed=%7.3f (Reason: %r)",
                    fwert, radangle, getattr(car, "power", 0.0), getattr(car, "speed", 0.0), _e
                )

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug(
                "ACTUATE: fwert=%5.1f swert=%5.1f -> clipped=%5.1f radangle=%6.2f° power=%6.2f speed=%7.3f px/tick",
                fwert, swert, clipped, radangle, car.power, car.speed
            )

    # ------------------------------------------------------------
    # C controller (if available), else fallback Python
    # ------------------------------------------------------------
    @staticmethod
    def regelungtechnik_c(cars: List[Any]) -> None:
        if not _NATIVE_OK or lib is None:
            log.debug("C controller not available → Using Python controller.")
            return Interface.regelungtechnik_python(cars)

        for car in cars:
            if not (getattr(car, "radars_enable", True) and getattr(car, "regelung_enable", True)):
                log.debug("C-SKIP: radars_enable=%s regelung_enable=%s", getattr(car, "radars_enable", None), getattr(car, "regelung_enable", None))
                continue
            if not getattr(car, "bit_volt_wert_list", None) or len(car.bit_volt_wert_list) < 3:
                # If this car lacks analog/sensor values, fall back to the Python
                # regulator for this car instead of silently skipping it.
                log.debug("C-SKIP: insufficient analog values: %s -> Fallback to Python controller for this car", getattr(car, "bit_volt_wert_list", None))
                try:
                    # Call python regulator for this single car to ensure outputs are applied
                    Interface.regelungtechnik_python([car])
                except Exception as _e:
                    log.debug("Fallback Python controller for car failed: %r", _e)
                continue

            try:
                # Set inputs
                # Caution: _set_power/_set_steer can be None, then except branch goes to Python fallback.
                _set_power(int(car.power))      # type: ignore[misc]
                _set_steer(int(car.radangle))   # type: ignore[misc]

                rechts = int(car.bit_volt_wert_list[0][0])
                vorne  = int(car.bit_volt_wert_list[1][0])
                links  = int(car.bit_volt_wert_list[2][0])

                radians = math.radians(getattr(car, "radar_angle", 0.0))
                # Cosine scaling: C side expects cos*100 where 100 == 1.0
                # Older code used *10 which caused distance scaling mismatch
                real_cos = math.cos(radians)
                # Scale to 0..100 (100 == cos==1.0), ensure at least 1 to avoid division-by-zero
                # Clamp to 1..255 (uint8 range)
                cosAlpha_scaled = int(round(real_cos * 100))
                if cosAlpha_scaled < 1:
                    cosAlpha_scaled = 1
                if cosAlpha_scaled > 255:
                    cosAlpha_scaled = 255
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("HEADING: radar_angle=%.2f deg radians=%.4f cos=%.4f scaled=%d",
                              getattr(car, "radar_angle", 0.0), radians, real_cos, cosAlpha_scaled)

                lib.getabstandvorne(vorne)
                lib.getabstandrechts(rechts, cosAlpha_scaled & 0xFF)  # C side expects unsigned char (0..255)
                lib.getabstandlinks(links,  cosAlpha_scaled & 0xFF)

                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug(
                        "C-IN: power=%4.0f radangle=%5.1f | bit(vorne/rechts/links)=(%d,%d,%d) cosAlpha_scaled=%d",
                        car.power, car.radangle, vorne, rechts, links, cosAlpha_scaled
                    )

                # Execute controller calculation
                lib.regelungtechnik()

                # Read outputs
                car.fwert = int(lib.getfwert())
                car.swert = int(lib.getswert())
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("C-OUT: fwert=%d swert=%d", car.fwert, car.swert)

            except Exception as e:
                log.error("C controller error: %r → Fallback to Python controller", e)
                return Interface.regelungtechnik_python(cars)

            # Apply actuation
            Interface._apply_outputs_to_car(car, car.fwert, car.swert)

    # ------------------------------------------------------------
    # Python Controller
    # ------------------------------------------------------------
    @staticmethod
    def regelungtechnik_python(cars: List[Any]) -> None:
        for car in cars:
            if not (getattr(car, "radars_enable", True) and getattr(car, "regelung_enable", True)):
                log.debug("PY-SKIP: radars_enable=%s regelung_enable=%s", getattr(car, "radars_enable", None), getattr(car, "regelung_enable", None))
                continue
            if not getattr(car, "radar_dist", None) or len(car.radar_dist) < 3:
                log.debug("PY-SKIP: insufficient radar distances: %s", getattr(car, "radar_dist", None))
                continue

            distcm = [model.sim_to_real(px) for px in car.radar_dist]
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "PY IN  dist(px)=%s  dist(cm)=%.1f/%.1f/%.1f",
                    getattr(car, "radar_dist", None), distcm[0], distcm[1], distcm[2]
                )

            # Lateral control (simple P)
            if distcm[0] < 130 or distcm[2] < 130:
                diff = distcm[2] - distcm[0]
                car.swert = -((diff - 0.0) * kp2)

            # Longitudinal control (P controller in three ranges)
            s1 = distcm[1] * k1
            s2 = distcm[1] * k2
            s3 = distcm[1] * k3

            if distcm[1] > 100:
                if car.power < 60:
                    car.fwert += (s1 - distcm[1]) * kp1 + 18
                    car.fwert = min(car.fwert, 60)
            elif 50 < distcm[1] <= 100:
                if car.power > 18:
                    car.fwert -= (s2 - distcm[1]) * kp1
                    car.fwert = max(car.fwert, 18)
            else:
                car.fwert = -(s3 - distcm[1]) * kp1 - 18
                car.swert = -(distcm[0] - distcm[2]) * kp2 - 10

            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug("PY OUT fwert=%6.2f swert=%6.2f", car.fwert, car.swert)

            # Apply actuation
            Interface._apply_outputs_to_car(car, car.fwert, car.swert)

    # ------------------------------------------------------------
    # Optional UI helpers – as no-op if your simulation calls them.
    # They import pygame locally to keep this module headless.
    # ------------------------------------------------------------
    @staticmethod
    def draw_dialog(screen) -> None:
        # Delegate to the canonical screen_service implementation. Keep a thin
        # wrapper here for API compatibility so callers of Interface.draw_dialog
        # continue to work.
        try:
            from ..sim import screen_service
            screen_service.draw_dialog(screen)
        except Exception:
            log.debug("draw_dialog: delegated draw_dialog failed (noop).")

    @staticmethod
    def draw_button(screen, text, text_color, button_color, positionx, positiony, button_width, button_height, button_rect) -> None:
        # Delegate to the canonical screen_service implementation. Keep a thin
        # wrapper for backwards compatibility with older code that calls
        # Interface.draw_button.
        try:
            from ..sim import screen_service
            screen_service.draw_button(screen, text, text_color, button_color, positionx, positiony, button_width, button_height, button_rect)
        except Exception:
            log.debug("draw_button: delegated draw_button failed (noop).")
        

    # ------------------------------------------------------------
    # Small C getters (useful for debugging native module)
    # ------------------------------------------------------------
    @staticmethod
    def getabstandvorne1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandvorne())
            except Exception as e:
                log.error("getabstandvorne1 Error: %r", e)
        return 0

    @staticmethod
    def getabstandlinks1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandlinks())
            except Exception as e:
                log.error("getabstandlinks1 Error: %r", e)
        return 0

    @staticmethod
    def getabstandrechts1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandrechts())
            except Exception as e:
                log.error("getabstandrechts1 Error: %r", e)
        return 0


__all__ = ["Interface", "k1", "k2", "k3", "kp1", "kp2"]
