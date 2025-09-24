import math
import pygame
from abc import ABC, abstractmethod

from crazycar.car import model  # neues Paket-Layout

# --- Native-Modul laden (bevorzugt). Fallback: Python-Regelung ---
try:
    # aus build_native.py gebautes *.pyd (muss im Importpfad liegen)
    from carsim_native import ffi, lib
    _NATIVE_OK = True
except Exception:
    ffi = None
    lib = None
    _NATIVE_OK = False

# --- Sim/Regelungs-Parameter ---
WIDTH = model.WIDTH
HEIGHT = model.HEIGHT

# Regelungsparameter (können extern überschrieben werden)
k1 = 1.1
k2 = 1.1
k3 = 1.1
kp1 = 1.1
kp2 = 1.1


class MyInterface(ABC):
    @staticmethod
    @abstractmethod
    def regelungtechnik_c(cars):
        ...

    @staticmethod
    @abstractmethod
    def regelungtechnik_python(cars):
        ...


class Interface(MyInterface):

    @staticmethod
    def regelungtechnik_c(cars):
        # Wenn kein natives Modul verfügbar ist -> direkt Python-Regelung nutzen
        if not _NATIVE_OK or lib is None:
            return Interface.regelungtechnik_python(cars)

        for car in cars:
            if car.radars_enable and car.regelung_enable and car.bit_volt_wert_list and len(car.bit_volt_wert_list) >= 3:
                # Eingänge an Regler übergeben
                lib.getfahr(int(car.power))
                lib.getservo(int(car.radangle))

                anlagewertrechts = int(car.bit_volt_wert_list[0][0])
                anlagewertvorne  = int(car.bit_volt_wert_list[1][0])
                anlagewertlinks  = int(car.bit_volt_wert_list[2][0])

                radians = math.radians(car.radar_angle)
                cosAlpha = int(math.cos(radians) * 10)

                lib.getabstandvorne(anlagewertvorne)
                lib.getabstandrechts(anlagewertrechts, cosAlpha)
                lib.getabstandlinks(anlagewertlinks,  cosAlpha)

                lib.regelungtechnik()

                # Ausgänge lesen
                car.fwert = int(lib.getfwert())
                car.swert = int(lib.getswert())

            # Stellgrößen auf Fahrzeug anwenden
            car.radangle = -car.servo2IstWinkel(car.getwinkel(car.swert))
            car.getmotorleistung(car.fwert)
            car.speed = car.Geschwindigkeit(car.power)

    @staticmethod
    def regelungtechnik_python(cars):
        for car in cars:
            if car.radars_enable and car.regelung_enable and car.radar_dist and len(car.radar_dist) >= 3:
                distcm = [model.sim_to_real(px) for px in car.radar_dist]

                # Richtung (Seitenabstand ausgleichen)
                if distcm[0] < 130 or distcm[2] < 130:
                    sollwert4 = 0
                    diff = distcm[2] - distcm[0]
                    car.swert = -((diff - sollwert4) * kp2)

                # Geschwindigkeit (einfacher P-Regler in drei Bereichen)
                sollwert1 = distcm[1] * k1
                sollwert2 = distcm[1] * k2
                sollwert3 = distcm[1] * k3

                if distcm[1] > 100:
                    if car.power < 60:
                        car.fwert += (sollwert1 - distcm[1]) * kp1 + 18
                        car.fwert = min(car.fwert, 60)

                elif 50 < distcm[1] <= 100:
                    if car.power > 18:
                        car.fwert -= (sollwert2 - distcm[1]) * kp1
                        car.fwert = max(car.fwert, 18)

                elif distcm[1] < 50:
                    car.fwert = -(sollwert3 - distcm[1]) * kp1 - 18
                    car.swert = -(distcm[0] - distcm[2]) * kp2 - 10

            # Stellgrößen auf Fahrzeug anwenden
            car.radangle = -car.servo2IstWinkel(car.getwinkel(car.swert))
            car.getmotorleistung(car.fwert)
            car.speed = car.Geschwindigkeit(car.power)

    @staticmethod
    def draw_dialog(screen):
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
    def draw_button(screen, text, text_color, button_color, positionx, positiony, button_width, button_height, button_rect):
        pygame.draw.rect(screen, button_color, (positionx, positiony, button_width, button_height))
        font = pygame.font.Font(None, 24)
        text_surface = font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=button_rect.center)
        screen.blit(text_surface, text_rect)

    @staticmethod
    def getabstandvorne1():
        if _NATIVE_OK and lib is not None:
            return lib.get_abstandvorne()
        return 0

    @staticmethod
    def getabstandlinks1():
        if _NATIVE_OK and lib is not None:
            return lib.get_abstandlinks()
        return 0

    @staticmethod
    def getabstandrechts1():
        if _NATIVE_OK and lib is not None:
            return lib.get_abstandrechts()
        return 0
