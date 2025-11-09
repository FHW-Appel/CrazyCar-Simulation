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
