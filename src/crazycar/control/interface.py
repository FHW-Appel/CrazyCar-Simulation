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
import time  # für delay_fn

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
# Sicherstellen, dass build/_cffi importierbar ist (auch im Child)
# --------------------------------------------------------------------
_build_dir: str | None = None
try:
    from crazycar.interop.build_tools import ensure_build_on_path
    _build_dir = ensure_build_on_path()
    if _build_dir and _build_dir not in sys.path:
        sys.path.insert(0, _build_dir)
except Exception as _e:
    log.debug("ensure_build_on_path fehlgeschlagen (ok, wird ohne versucht): %r", _e)

# --------------------------------------------------------------------
# Robusteren Import / Symbol-Self-Test für das native Modul
# --------------------------------------------------------------------
REQUIRED_ANY_POWER = ("getfahr", "fahr")
REQUIRED_ANY_STEER = ("getservo", "servo")
REQUIRED_ALWAYS = (
    "regelungtechnik", "getfwert", "getswert",
    "getabstandvorne", "getabstandrechts", "getabstandlinks",
)


def _prefer_build_import() -> tuple[bool, Any, Any, str]:
    """
    Importiert crazycar.carsim_native bevorzugt aus build/_cffi und prüft
    die benötigten Symbole. Rückgabe: (ok, ffi, lib, mod_file)
    """
    build_dir = None
    try:
        from crazycar.interop.build_tools import ensure_build_on_path
        build_dir = ensure_build_on_path()
    except Exception:
        build_dir = None

    # clean import state
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
# Optional: natives C-Modul laden (Fallback auf Python-Regler)
# Erzwinge, dass es – wenn möglich – aus build/_cffi kommt.
# --------------------------------------------------------------------
ffi = None
lib = None
_NATIVE_OK = False
try:
    ok, ffi, lib, mf = _prefer_build_import()
    _NATIVE_OK = bool(ok)
    if _NATIVE_OK:
        log.info("Native Modul geladen: %s (C-Regler verfügbar).", mf)
        if os.getenv("CRAZYCAR_DEBUG") == "1":
            have = lambda n: hasattr(lib, n)
            log.debug(
                "carsim_native Symbole: getfahr=%s, fahr=%s, getservo=%s, servo=%s, "
                "getfwert=%s, getswert=%s, regelungtechnik=%s",
                have("getfahr"), have("fahr"), have("getservo"), have("servo"),
                have("getfwert"), have("getswert"), have("regelungtechnik")
            )
    else:
        log.error("Natives Modul geladen (%s), aber Symbole fehlen → Fallback auf Python-Regler.", mf)
except Exception as e:
    log.warning("Kein natives Modul verfügbar, nutze Python-Regler. Grund: %r", e)

# Optional: harte Vorgabe, dass C-Regler vorhanden sein muss
if os.getenv("CRAZYCAR_FORCE_C") == "1" and not _NATIVE_OK:
    raise RuntimeError("CRAZYCAR_FORCE_C=1 gesetzt, aber C-Regler nicht verfügbar oder unvollständig.")

# ------------------------------------------------------------
# Setter-Resolver (einmalig auflösen, dann direkt callen)
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
        # Nicht hart abbrechen – Python-Regler übernimmt unten automatisch
        missing = []
        if _set_power is None:
            missing.append("getfahr/fahr")
        if _set_steer is None:
            missing.append("getservo/servo")
        log.error("C-Regler: fehlende Setter (%s) – Fallback auf Python-Regler.", ", ".join(missing))
        _NATIVE_OK = False

# --------------------------------------------------------------------
# Sim-/Regelungs-Parameter
# --------------------------------------------------------------------
WIDTH = model.WIDTH
HEIGHT = model.HEIGHT

# Diese Werte kann dein Optimizer überschreiben (per Dateiedit)
k1 = 1.10000001
k2 = 1.1
k3 = 1.1
kp1 = 1.1
kp2 = 1.1


class MyInterface(ABC):
    @staticmethod
    @abstractmethod
    def regelungtechnik_c(cars: List[Any]) -> None: ...
    @staticmethod
    @abstractmethod
    def regelungtechnik_python(cars: List[Any]) -> None: ...


class Interface(MyInterface):
    # ------------------------------------------------------------
    # Hilfsfunktion: Regler-Ausgänge ins Fahrzeug anwenden
    # ------------------------------------------------------------
    @staticmethod
    def _apply_outputs_to_car(car, fwert: float, swert: float) -> None:
        """Aktorik anwenden + Log-Ausgaben."""
        # Lenkung
        clipped = clip_steer(swert)
        radangle = -servo_to_angle(clipped)
        car.radangle = radangle
        # --- NEU: Leistungs-Mapping inklusive Deadzone/Min-Start nutzen ---
        # Parametrierung: maxpower=100, delay_fn noop (kein echtes Warten im Sim-Loop)
        try:
            maxpower = 100.0
            current_speed = getattr(car, "speed", 0.0)
            new_power, new_speed = apply_power(
                fwert=fwert,
                current_power=getattr(car, "power", 0.0),
                current_speed_px=current_speed,
                maxpower=maxpower,
                speed_fn=car.Geschwindigkeit,
                delay_fn=lambda ms: None,  # oder: lambda ms: time.sleep(ms/1000)
            )

            # **State setzen** – erst power, dann legacy-Paths synchronisieren
            car.power = new_power
            # Legacy-Side-Effects beibehalten:
            try:
                car.getmotorleistung(new_power)
            except Exception:
                # falls getmotorleistung kein Setter ist, nicht schlimm
                pass

            # Geschwindigkeit konsistent setzen
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
            # Fallback: altes Verhalten unverändert lassen
            try:
                car.getmotorleistung(fwert)
            except Exception:
                pass
            try:
                car.speed = car.Geschwindigkeit(car.power)
            except Exception:
                # leave speed as-is if even this fails
                pass
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "ACTUATE_FALLBACK: fwert=%5.1f radangle=%6.2f° power=%6.2f speed=%7.3f (Grund: %r)",
                    fwert, radangle, getattr(car, "power", 0.0), getattr(car, "speed", 0.0), _e
                )

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug(
                "ACTUATE: fwert=%5.1f swert=%5.1f -> clipped=%5.1f radangle=%6.2f° power=%6.2f speed=%7.3f px/tick",
                fwert, swert, clipped, radangle, car.power, car.speed
            )

    # ------------------------------------------------------------
    # C-Regler (wenn verfügbar), sonst Fallback Python
    # ------------------------------------------------------------
    @staticmethod
    def regelungtechnik_c(cars: List[Any]) -> None:
        if not _NATIVE_OK or lib is None:
            log.debug("C-Regler nicht verfügbar → Python-Regler wird genutzt.")
            return Interface.regelungtechnik_python(cars)

        for car in cars:
            if not (getattr(car, "radars_enable", True) and getattr(car, "regelung_enable", True)):
                log.debug("C-SKIP: radars_enable=%s regelung_enable=%s", getattr(car, "radars_enable", None), getattr(car, "regelung_enable", None))
                continue
            if not getattr(car, "bit_volt_wert_list", None) or len(car.bit_volt_wert_list) < 3:
                # If this car lacks analog/sensor values, fall back to the Python
                # regulator for this car instead of silently skipping it. Skipping
                # left the car uncontrolled and produced the constant-speed symptom.
                log.debug("C-SKIP: zu wenige analog Werte: %s -> Fallback auf Python-Regler für dieses Auto", getattr(car, "bit_volt_wert_list", None))
                try:
                    # Call python regulator for this single car to ensure outputs are applied
                    Interface.regelungtechnik_python([car])
                except Exception as _e:
                    log.debug("Fallback-Python-Regler für Car schlug fehl: %r", _e)
                continue

            try:
                # Eingänge setzen
                # Achtung: _set_power/_set_steer können None sein, dann geht der except-Zweig in den Python-Fallback.
                _set_power(int(car.power))      # type: ignore[misc]
                _set_steer(int(car.radangle))   # type: ignore[misc]

                rechts = int(car.bit_volt_wert_list[0][0])
                vorne  = int(car.bit_volt_wert_list[1][0])
                links  = int(car.bit_volt_wert_list[2][0])

                radians = math.radians(getattr(car, "radar_angle", 0.0))
                # Cosinus: radians is angle in degrees converted to radians above.
                # The native C linearisierung expects the cosine scaled such that
                # 100 == 1.0 (i.e. cos*100). Older code used *10 which caused
                # a mismatch in distance scaling between Python and C.
                real_cos = math.cos(radians)
                # scale to 0..100 (100 == cos==1.0). Ensure at least 1 to avoid
                # division-by-zero in the C side. Clamp to 1..255 (uint8 range).
                cosAlpha_scaled = int(round(real_cos * 100))
                if cosAlpha_scaled < 1:
                    cosAlpha_scaled = 1
                if cosAlpha_scaled > 255:
                    cosAlpha_scaled = 255
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("HEADING: radar_angle=%.2f deg radians=%.4f cos=%.4f scaled=%d",
                              getattr(car, "radar_angle", 0.0), radians, real_cos, cosAlpha_scaled)

                lib.getabstandvorne(vorne)
                lib.getabstandrechts(rechts, cosAlpha_scaled & 0xFF)  # C-Seite erwartet unsigned char (0..255)
                lib.getabstandlinks(links,  cosAlpha_scaled & 0xFF)

                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug(
                        "C-IN: power=%4.0f radangle=%5.1f | bit(vorne/rechts/links)=(%d,%d,%d) cosAlpha_scaled=%d",
                        car.power, car.radangle, vorne, rechts, links, cosAlpha_scaled
                    )

                # Regler rechnen lassen
                lib.regelungtechnik()

                # Ausgänge lesen
                car.fwert = int(lib.getfwert())
                car.swert = int(lib.getswert())
                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug("C-OUT: fwert=%d swert=%d", car.fwert, car.swert)

            except Exception as e:
                log.error("C-Regler Fehler: %r → Fallback auf Python-Regler", e)
                return Interface.regelungtechnik_python(cars)

            # Aktorik anwenden
            Interface._apply_outputs_to_car(car, car.fwert, car.swert)

    # ------------------------------------------------------------
    # Python-Regler
    # ------------------------------------------------------------
    @staticmethod
    def regelungtechnik_python(cars: List[Any]) -> None:
        for car in cars:
            if not (getattr(car, "radars_enable", True) and getattr(car, "regelung_enable", True)):
                log.debug("PY-SKIP: radars_enable=%s regelung_enable=%s", getattr(car, "radars_enable", None), getattr(car, "regelung_enable", None))
                continue
            if not getattr(car, "radar_dist", None) or len(car.radar_dist) < 3:
                log.debug("PY-SKIP: zu wenige Radar-Distanzen: %s", getattr(car, "radar_dist", None))
                continue

            distcm = [model.sim_to_real(px) for px in car.radar_dist]
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "PY IN  dist(px)=%s  dist(cm)=%.1f/%.1f/%.1f",
                    getattr(car, "radar_dist", None), distcm[0], distcm[1], distcm[2]
                )

            # Seitenführung (einfacher P)
            if distcm[0] < 130 or distcm[2] < 130:
                diff = distcm[2] - distcm[0]
                car.swert = -((diff - 0.0) * kp2)

            # Längsführung (P-Regler in drei Bereichen)
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

            # Aktorik anwenden
            Interface._apply_outputs_to_car(car, car.fwert, car.swert)

    # ------------------------------------------------------------
    # Optionale UI-Helfer – als No-Op, falls deine Simulation sie aufruft.
    # Sie importieren pygame erst lokal, damit dieses Modul headless bleibt.
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
    # Kleine C-Getter (nützlich fürs Debuggen des nativen Moduls)
    # ------------------------------------------------------------
    @staticmethod
    def getabstandvorne1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandvorne())
            except Exception as e:
                log.error("getabstandvorne1 Fehler: %r", e)
        return 0

    @staticmethod
    def getabstandlinks1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandlinks())
            except Exception as e:
                log.error("getabstandlinks1 Fehler: %r", e)
        return 0

    @staticmethod
    def getabstandrechts1() -> int:
        if _NATIVE_OK and lib is not None:
            try:
                return int(lib.get_abstandrechts())
            except Exception as e:
                log.error("getabstandrechts1 Fehler: %r", e)
        return 0


__all__ = ["Interface", "k1", "k2", "k3", "kp1", "kp2"]
