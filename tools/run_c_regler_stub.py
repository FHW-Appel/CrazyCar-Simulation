"""Kurzes Testskript: erstellt ein Car-Stub und ruft Interface.regelungtechnik_c auf.

Zweck: prüft, ob die C-Regler-Pfade aktiv sind und ob ACTUATE_MAP logs erscheinen.
"""
from __future__ import annotations
import os
import time
import sys
from pathlib import Path

# Ensure src and build/_cffi are on sys.path so imports find the compiled module
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
BUILD = ROOT / 'build' / '_cffi'
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(SRC))

# Debug/Deadzone kurz für Test konfigurieren
os.environ["CRAZYCAR_DEBUG"] = "1"
os.environ["CRAZYCAR_MOTOR_DEADZONE"] = "5"

# Projekt-Imports (now with correct sys.path)
from crazycar.control.interface import Interface

class CarStub:
    def __init__(self):
        # Aktorik/State
        self.power = 0.0
        self.speed = 0.0
        self.radangle = 0.0
        self.carangle = 0.0
        self.fwert = 0.0
        self.swert = 0.0
        self.speed_set = 0.0
        self.maxpower = 100

        # Sensor/Flags
        self.radars_enable = True
        self.regelung_enable = True
        self.radar_angle = 60.0
        # bit_volt_wert_list: list of (digital_bit, analog_volt)
        # ordering expected in Interface: [rechts, vorne, links]
        # initial values represent a moderate distance (will be changed per-iteration)
        self.bit_volt_wert_list = [ (200, 0.0), (200, 0.0), (200, 0.0) ]
        self.radar_dist = [200, 200, 200]

    def Geschwindigkeit(self, power: float) -> float:
        # simple linear speed model for testing
        new_speed = float(power) * 0.03
        self.speed = new_speed
        return new_speed

    def getmotorleistung(self, fwert):
        # legacy setter
        self.power = float(fwert)
        # adjust speed to match
        self.Geschwindigkeit(self.power)

    def is_alive(self):
        return True


if __name__ == '__main__':
    car = CarStub()
    print("Starting C-regler stub test: calling Interface.regelungtechnik_c 5x")
    # Test a sequence of increasing proximity values to simulate approaching a wall
    test_bits = [200, 300, 400, 500, 700]  # larger digital bit -> smaller distance
    for i, bits in enumerate(test_bits, start=1):
        print(f"--- Iteration {i} (bits={bits}) ---")
        car.bit_volt_wert_list = [(bits, 0.0), (bits, 0.0), (bits, 0.0)]
        try:
            Interface.regelungtechnik_c([car])
        except Exception as e:
            print("Exception during C-regler call:", e)
        print(f"Resulting car.fwert={car.fwert} car.swert={car.swert} power={car.power} speed={car.speed}")
        time.sleep(0.1)
    print("Done.")
