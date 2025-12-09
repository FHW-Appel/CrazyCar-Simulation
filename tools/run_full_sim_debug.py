# tools/run_full_sim_debug.py
"""
Run the CrazyCar direct (DLL-only) simulation with debug logging enabled.
This script sets the environment variables before importing the simulation module
so module-level loggers pick up CRAZYCAR_DEBUG.

Usage (from repo root):
    python tools/run_full_sim_debug.py [seconds]

Defaults to 20 seconds.
"""
import os
import sys
import time

# Ensure src is in sys.path
REPO_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if REPO_SRC not in sys.path:
    sys.path.insert(0, REPO_SRC)

# Set debug + motor deadzone before importing the sim module
os.environ['CRAZYCAR_DEBUG'] = '1'
os.environ['CRAZYCAR_MOTOR_DEADZONE'] = os.environ.get('CRAZYCAR_MOTOR_DEADZONE', '5')
# Ensure we start in C-regler/direct mode
os.environ['CRAZYCAR_START_PYTHON'] = os.environ.get('CRAZYCAR_START_PYTHON', '0')

# Duration
try:
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
except Exception:
    dur = 20.0

print(f"[run_full_sim_debug] CRAZYCAR_DEBUG={os.environ['CRAZYCAR_DEBUG']} DUR={dur}s")

# Importing simulation after env is set so logging config is correct
from crazycar.sim.simulation import run_direct

# Zusatz: Kurzer MapService-Check vor dem Sim-Start, damit Spawn-Detection
# eindeutig im Full-Sim-Log auftaucht (Debug-Hilfe).
try:
    import pygame
    from crazycar.sim.map_service import MapService
    pygame.init()
    # Nutze moderate Fenstergröße für die Erkennung — verändert nichts an der Sim
    try:
        ms = MapService((1024, 768))
        spawn = ms.get_spawn()
        info = ms.get_detect_info()
        # Very explicit, flushed prints so the pre-sim detection is easy to spot
        print("\n" + "=" * 60, flush=True)
        print(f"[run_full_sim_debug] get_spawn() -> {spawn}", flush=True)
        if info is None:
            print("[run_full_sim_debug] detect_info: <None>", flush=True)
        else:
            print(f"[run_full_sim_debug] detect_info summary:", flush=True)
            print(f"  n={info.get('n',0)}  bbox=({info.get('minx')},{info.get('miny')})-({info.get('maxx')},{info.get('maxy')})", flush=True)
            print(f"  cx={info.get('cx',0):.1f}, cy={info.get('cy',0):.1f}", flush=True)
            print(f"  vx={info.get('vx',0):.3f}, vy={info.get('vy',0):.3f}", flush=True)
            print(f"  nx={info.get('nx',0):.3f}, ny={info.get('ny',0):.3f} sign={info.get('sign')}", flush=True)
        print("" + "=" * 60 + "\n", flush=True)
    except Exception as e:
        print("[run_full_sim_debug] MapService detect failed:", e)
    # leave pygame running for the sim (do not quit)
except Exception:
    # Falls pygame/MapService nicht verfügbar — ignoriere die Vorab-Prüfung
    pass

# Run and measure
start = time.time()
try:
    run_direct(duration_s=dur)
except SystemExit:
    pass
except Exception as e:
    print("[run_full_sim_debug] Exception during run:", e)

end = time.time()
print(f"[run_full_sim_debug] finished after {end - start:.2f}s")
