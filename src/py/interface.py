import pygame
import math
import time
from abc import ABC, abstractmethod
import os
import car

# --- Versuch: natives CFFI-Modul laden (bevorzugt) ---
try:
    from carsim_native import ffi, lib  # aus build_native.py gebautes *.pyd
    _NATIVE_OK = True
except Exception:
    _NATIVE_OK = False
    import cffi
    ffi = cffi.FFI()

    # Signaturen müssen exakt zu den C-Headern passen
    ffi.cdef(r"""
        void     fahr(int f);
        int      getfwert(void);
        void     servo(int s);
        int      getswert(void);

        void     getfahr(int8_t leistung);
        void     getservo(int8_t winkel);

        void     getabstandvorne(uint16_t analogwert);
        void     getabstandrechts(uint16_t analogwert, uint8_t cosAlpha);
        void     getabstandlinks(uint16_t analogwert, uint8_t cosAlpha);

        void     regelungtechnik(void);

        int8_t   getFahr(void);
        int8_t   getServo(void);
        uint16_t get_abstandvorne(void);
        uint16_t get_abstandrechts(void);
        uint16_t get_abstandlinks(void);
    """)

    # DLL-Pfad aus config_interface.txt (liegt neben dieser Datei)
    def get_dll_path() -> str:
        config_path = os.path.join(os.path.dirname(__file__), "config_interface.txt")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DLL_PATH="):
                        return line.strip().split("=", 1)[1]
        except Exception as e:
            print("Fehler beim Laden des DLL-Pfads:", e)
        return ""

    _dll_path = get_dll_path()
    if not _dll_path:
        raise OSError("DLL-Pfad konnte nicht aus config_interface.txt geladen werden.")
    lib = ffi.dlopen(_dll_path)

# --- Sim/Regelungs-Parameter ---
f = car.f
WIDTH = 1920 * f
HEIGHT = 1080 * f

# Regelungsparameter (werden ggf. überschrieben)
k1 = 1.1
k2 = 1.1
k3 = 1.1
kp1 = 1.1
kp2 = 1.1


class MyInterface(ABC):
    @abstractmethod
    def regelungtechnik_c(self): 
        pass

    @abstractmethod
    def regelungtechnik_python(self): 
        pass


class Interface(MyInterface):

    @staticmethod
    def regelungtechnik_c(cars):
        for car in cars:
            if car.radars_enable and car.regelung_enable:
                lib.getfahr(int(car.power))
                lib.getservo(int(car.radangle))

                anlagewertrechts = car.bit_volt_wert_list[0][0]
                anlagewertvorne = car.bit_volt_wert_list[1][0]
                anlagewertlinks = car.bit_volt_wert_list[2][0]

                radians = math.radians(car.radar_angle)
                cosAlpha = int(math.cos(radians) * 10)

                lib.getabstandvorne(anlagewertvorne)
                lib.getabstandrechts(anlagewertrechts, cosAlpha)
                lib.getabstandlinks(anlagewertlinks, cosAlpha)

                lib.regelungtechnik()
                car.fwert = lib.getfwert()
                car.swert = lib.getswert()

            car.radangle = -car.servo2IstWinkel(car.getwinkel(car.swert))
            car.getmotorleistung(car.fwert)
            car.speed = car.Geschwindigkeit(car.power)

    @staticmethod
    def regelungtechnik_python(cars):
        for car in cars:
            if car.radars_enable and car.regelung_enable:
                distcm = [sim_to_real(px) for px in car.radar_dist]

                # Richtung
                if distcm[0] < 130 or distcm[2] < 130:
                    sollwert4 = 0
                    diff = distcm[2] - distcm[0]
                    car.swert = -((diff - sollwert4) * kp2)

                # Geschwindigkeit
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
        return lib.get_abstandvorne()

    @staticmethod
    def getabstandlinks1():
        return lib.get_abstandlinks()

    @staticmethod
    def getabstandrechts1():
        return lib.get_abstandrechts()


# --- Hilfsfunktionen ---
def sim_to_real(simpx):
    return (simpx * 1900) / WIDTH

def real_to_sim(realcm):
    return realcm * WIDTH / 1900
