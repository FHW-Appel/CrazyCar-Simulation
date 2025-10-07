# src/crazycar/main.py
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path

# Einfacher Debug-Schalter: 0 = aus, 1 = an 
DEBUG_DEFAULT = 0

_THIS = Path(__file__).resolve()
_SRC_DIR = _THIS.parents[1]  # .../src
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
print("[sys.path add]", _SRC_DIR)

from crazycar.interop.build_tools import run_build_native  # nur Build-Tool vorab importieren

def main() -> int:
    # Debug initialisieren (nur über den Schalter oben)
    debug = bool(int(DEBUG_DEFAULT))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s"
    )
    logging.info("Starting CrazyCar (debug=%s)", debug)
    os.environ["CRAZYCAR_DEBUG"] = "1" if debug else "0"

    # Native Build 
    try:
        rc, build_out_dir = run_build_native()
        if rc != 0:
            print("[ERROR] Native Build fehlgeschlagen (Exit 1).")
        else:
            # Build-/cffi-Ordner nach vorne, damit 'crazycar.carsim_native' von dort kommt
            if build_out_dir and build_out_dir not in sys.path:
                sys.path.insert(0, build_out_dir)
                print("[sys.path add build]", build_out_dir)
            # Optionaler Hint für interface.py, falls du dort darauf reagierst:
            os.environ["CRAZYCAR_NATIVE_PATH"] = build_out_dir
    except Exception as e:
        print(f"[ERROR] Native Build Exception: {e}")

    # Jetzt erst optimizer importieren 
    from crazycar.control.optimizer import run_optimization

    res = run_optimization()
    print("Optimierte Parameter:")
    print(f"K1: {res['k1']}")
    print(f"K2: {res['k2']}")
    print(f"K3: {res['k3']}")
    print(f"Kp1: {res['kp1']}")
    print(f"Kp2: {res['kp2']}")
    print(f"Optimale Rundenzeit: {res['optimal_lap_time']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Sauber abbrechen ohne langer Traceback, wenn du STRG+C drückst
        print("\n[main] Abgebrochen (Ctrl+C).")
        sys.exit(130)
