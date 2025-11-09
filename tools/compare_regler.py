#!/usr/bin/env python3
"""Compare C vs Python regulator outputs for a grid of sensor inputs.

Produces a simple CSV-like report to stdout showing fwert/swert from both
regulators and the differences.

Run from repo root: python tools/compare_regler.py
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from crazycar.control.interface import Interface


@dataclass
class DummyCar:
    # minimal attributes used by the Interface regulators
    radar_dist: List[int]
    bit_volt_wert_list: List[Tuple[int, float]]
    power: float = 0.0
    radangle: float = 0.0
    speed: float = 0.0
    radar_angle: float = 60.0
    radars_enable: bool = True
    regelung_enable: bool = True

    # attributes written by regulator
    fwert: float = 0.0
    swert: float = 0.0

    # API compatibility stubs
    def Geschwindigkeit(self, power: float) -> float:
        # simple mapping used only for compatibility with apply_power
        try:
            from crazycar.car.model import Car
            # use model's helper if available (safe path)
            return Car.Geschwindigkeit.__get__(self, Car)(power)
        except Exception:
            return float(power) * 0.004  # fallback: small proportional speed

    def getmotorleistung(self, p: float):
        # legacy hook used in Interface._apply_outputs_to_car; no-op
        self.power = p


def run_grid() -> None:
    # use a reasonable grid of real distances (cm) and radar angles
    # we'll derive the DA digital_bit and pixel distances from these
    dist_cm_values = [20.0, 40.0, 60.0, 100.0, 200.0]
    radar_angles = [60.0, 30.0, 0.0, -30.0, -60.0]

    # print header
    print("front, right, left, radar_angle, py_f, py_s, c_f, c_s, df, ds")

    # create pairs for all combinations (cartesian)
    # helpers from sensors/units to create consistent inputs
    from crazycar.car.sensors import linearize_DA
    from crazycar.car.units import real_to_sim

    for front_cm in dist_cm_values:
        for right_cm in dist_cm_values:
            for left_cm in dist_cm_values:
                for ra in radar_angles:
                    # prepare inputs consistently from real cm distances
                    # Python regulator expects pixel distances; C regulator expects DA bit/volt
                    py_px_center = [int(real_to_sim(right_cm)), int(real_to_sim(front_cm)), int(real_to_sim(left_cm))]
                    # compute DA linearisierung (bit, volt) from cm values
                    bitlist_front = linearize_DA([front_cm])[0]
                    bitlist_right = linearize_DA([right_cm])[0]
                    bitlist_left = linearize_DA([left_cm])[0]
                    bitlist = [bitlist_right, bitlist_front, bitlist_left]

                    car_py = DummyCar(radar_dist=py_px_center.copy(), bit_volt_wert_list=bitlist.copy(), power=0.0, radangle=0.0, radar_angle=ra)
                    car_c  = DummyCar(radar_dist=py_px_center.copy(), bit_volt_wert_list=bitlist.copy(), power=0.0, radangle=0.0, radar_angle=ra)

                    # Run Python regulator
                    try:
                        Interface.regelungtechnik_python([car_py])
                    except Exception as e:
                        print(f"ERROR running python regulator: {e}", file=sys.stderr)
                        continue

                    # Run C regulator (if available)
                    try:
                        Interface.regelungtechnik_c([car_c])
                    except Exception as e:
                        # If C not available, print placeholder and continue
                        print(f"{front_cm},{right_cm},{left_cm},{ra}, {car_py.fwert:.2f},{car_py.swert:.2f}, NA, NA, NA, NA")
                        continue

                    df = car_py.fwert - getattr(car_c, "fwert", 0.0)
                    ds = car_py.swert - getattr(car_c, "swert", 0.0)
                    print(f"{front_cm},{right_cm},{left_cm},{ra},{car_py.fwert:.2f},{car_py.swert:.2f},{car_c.fwert:.2f},{car_c.swert:.2f},{df:.2f},{ds:.2f}")


if __name__ == "__main__":
    run_grid()
