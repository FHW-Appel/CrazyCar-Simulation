# src/crazycar/main.py
import sys
from pathlib import Path

# --- Pfadfix: "src" in sys.path aufnehmen, damit 'crazycar' importierbar ist ---
_THIS = Path(__file__).resolve()
_SRC_DIR = _THIS.parent.parent  # .../CrazyCar-Simulation/src
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Alt (auskommentiert beibehalten):
# from .interop.build_tools import run_build_native
# from .control.optimizer import run_optimization

# Neu: absolute Paket-Imports (funktionieren dank sys.path-Fix)
from crazycar.interop.build_tools import run_build_native
from crazycar.control.optimizer import run_optimization


def main() -> int:
    try:
        run_build_native()
    except Exception as e:
        print(f"[WARN] Native build failed ({e}). Falling back to Python controller.")

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
    sys.exit(main())
