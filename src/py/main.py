# src/py/main.py
import sys
from utils.build_tools import run_build_native

def main() -> int:
    # 1) CFFI-Build (nur fortfahren, wenn OK)
    rc = run_build_native()
    if rc != 0:
        return rc

    # 2) Optimierung starten
    from simulate_car import run_optimization
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
