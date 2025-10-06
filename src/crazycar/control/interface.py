# crazycar/control/interface.py
from __future__ import annotations
import os
import math
import logging
from abc import ABC, abstractmethod
from typing import List, Any

from crazycar.car import model
from crazycar.car.actuation import servo_to_angle, clip_steer

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
# Optional: natives C-Modul laden (Fallback auf Python-Regler)
# --------------------------------------------------------------------
try:
    from crazycar.carsim_native import ffi, lib
    _NATIVE_OK = True
    log.info("Native Modul geladen: crazycar.carsim_native (C-Regler verfügbar).")
except Exception as e:
    ffi = None
    lib = None
    _NATIVE_OK = False
    log.warning("Kein natives Modul verfügbar, nutze Python-Regler. Grund: %r", e)

# --------------------------------------------------------------------
# Sim-/Regelungs-Parameter
# --------------------------------------------------------------------
WIDTH = model.WIDTH
HEIGHT = model.HEIGHT

# Diese Werte kann dein Optimizer überschreiben (per Dateiedit)
k1 = 1.1
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

        # Motorleistung (passt intern speed an)
        car.getmotorleistung(fwert)
        car.speed = car.Geschwindigkeit(car.power)

        if os.getenv("CRAZYCAR_DEBUG") == "1":
            log.debug(
                "ACTUATE: fwert=%5.1f swert=%5.1f -> clipped=%5.1f radangle=%6.2f° "
                "power=%6.2f speed=%7.3f px/tick",
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
                log.debug("C-SKIP: radars_enable=%s regelung_enable=%s", car.radars_enable, car.regelung_enable)
                continue
            if not getattr(car, "bit_volt_wert_list", None) or len(car.bit_volt_wert_list) < 3:
                log.debug("C-SKIP: zu wenige analog Werte: %s", getattr(car, "bit_volt_wert_list", None))
                continue

            try:
                # Eingänge setzen
                lib.getfahr(int(car.power))
                lib.getservo(int(car.radangle))

                rechts = int(car.bit_volt_wert_list[0][0])
                vorne  = int(car.bit_volt_wert_list[1][0])
                links  = int(car.bit_volt_wert_list[2][0])

                radians = math.radians(car.radar_angle)
                cosAlpha = int(math.cos(radians) * 10)

                lib.getabstandvorne(vorne)
                lib.getabstandrechts(rechts, cosAlpha)
                lib.getabstandlinks(links,  cosAlpha)

                if os.getenv("CRAZYCAR_DEBUG") == "1":
                    log.debug(
                        "C-IN: power=%4.0f radangle=%5.1f | bit(vorne/rechts/links)=(%d,%d,%d) cosAlpha=%d",
                        car.power, car.radangle, vorne, rechts, links, cosAlpha
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
                log.debug("PY-SKIP: radars_enable=%s regelung_enable=%s", car.radars_enable, car.regelung_enable)
                continue
            if not getattr(car, "radar_dist", None) or len(car.radar_dist) < 3:
                log.debug("PY-SKIP: zu wenige Radar-Distanzen: %s", getattr(car, "radar_dist", None))
                continue

            distcm = [model.sim_to_real(px) for px in car.radar_dist]
            if os.getenv("CRAZYCAR_DEBUG") == "1":
                log.debug(
                    "PY IN  dist(px)=%s  dist(cm)=%.1f/%.1f/%.1f",
                    car.radar_dist, distcm[0], distcm[1], distcm[2]
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
        try:
            import pygame
        except Exception:
            log.debug("draw_dialog: pygame nicht verfügbar (noop).")
            return

        dialog_width = 500
        dialog_height = 200
        dialog_x = (WIDTH - dialog_width) // 2
        dialog_y = (HEIGHT - dialog_height) // 2

        dialog_surface = pygame.Surface((dialog_width, dialog_height))
        dialog_surface.fill((255, 255, 255))
        pygame.draw.rect(dialog_surface, (0, 0, 0), (0, 0, dialog_width, dialog_height), 4)

        font = pygame.font.Font(None, 24)
        text = font.render("Sind Sie sicher, dass Sie die Regelungstechnik ändern wollen?", True, (0, 0, 0))
        text_rect = text.get_rect(center=(dialog_width // 2, dialog_height // 2 - 20))
        dialog_surface.blit(text, text_rect)

        screen.blit(dialog_surface, (dialog_x, dialog_y))
        pygame.display.flip()

    @staticmethod
    def draw_button(screen, text, text_color, button_color, positionx, positiony, button_width, button_height, button_rect) -> None:
        try:
            import pygame
        except Exception:
            log.debug("draw_button: pygame nicht verfügbar (noop).")
            return

        pygame.draw.rect(screen, button_color, (positionx, positiony, button_width, button_height))
        font = pygame.font.Font(None, 24)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)

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
