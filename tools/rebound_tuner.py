"""Simple tuner for rebound parameters.
Scans several ENV variable combinations, calls rebound_action with a representative
impact angle/speed and ranks parameter sets by a heuristic score (lower is better).

Run from repo root: python tools/rebound_tuner.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from itertools import product

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from crazycar.car.rebound import rebound_action

# Representative impact parameters
POINT0 = (100.0, 100.0)
NR = 1
CARANGLE = 20.0  # degrees between velocity and wall normal to exercise small/med/large damping
SPEED = 5.0
BORDER_COLOR = (255, 255, 255, 255)

# Grid of candidate values (kept modest)
DAMP_SMALL = [0.8, 0.25, 0.1]
DAMP_MED = [0.5, 0.15]
DAMP_LARGE = [0.2, 0.05]
K0 = [-1.7, -0.6, -0.2]
S_FACTOR = [8.0, 3.0, 1.0]
TURN_FACTOR = [7.0, 2.0, 1.0]
TURN_OFFSET = [1.0, 0.5]

results = []

# color_at dummy: always returns not-border so rebound_action uses default x1=x0+radius_px
# that is OK for our metric (we want to exercise angle-based damping)
def color_at_dummy(pt):
    return (0, 0, 0, 0)

count = 0
for ds, dm, dl, k0, sf, tf, to in product(
    DAMP_SMALL, DAMP_MED, DAMP_LARGE, K0, S_FACTOR, TURN_FACTOR, TURN_OFFSET
):
    count += 1
    # set env vars for the function (it reads them at call-time)
    os.environ["CRAZYCAR_REBOUND_DAMP_SMALL"] = str(ds)
    os.environ["CRAZYCAR_REBOUND_DAMP_MED"] = str(dm)
    os.environ["CRAZYCAR_REBOUND_DAMP_LARGE"] = str(dl)
    os.environ["CRAZYCAR_REBOUND_K0"] = str(k0)
    os.environ["CRAZYCAR_REBOUND_S_FACTOR"] = str(sf)
    os.environ["CRAZYCAR_REBOUND_TURN_FACTOR"] = str(tf)
    os.environ["CRAZYCAR_REBOUND_TURN_OFFSET"] = str(to)

    new_speed, new_angle, (dx, dy), slowed = rebound_action(
        POINT0, NR, CARANGLE, SPEED, color_at_dummy, BORDER_COLOR
    )

    pos_mag = abs(dx) + abs(dy)
    # minimal signed angular difference
    diff = (new_angle - CARANGLE + 180.0) % 360.0 - 180.0
    turn_mag = abs(diff)

    # score: weighted: new_speed (primary) + pos_mag*0.2 + turn_mag*0.05
    score = new_speed * 2.0 + pos_mag * 0.5 + turn_mag * 0.2

    results.append({
        "score": score,
        "new_speed": new_speed,
        "pos_mag": pos_mag,
        "turn_mag": turn_mag,
        "params": {
            "CRAZYCAR_REBOUND_DAMP_SMALL": ds,
            "CRAZYCAR_REBOUND_DAMP_MED": dm,
            "CRAZYCAR_REBOUND_DAMP_LARGE": dl,
            "CRAZYCAR_REBOUND_K0": k0,
            "CRAZYCAR_REBOUND_S_FACTOR": sf,
            "CRAZYCAR_REBOUND_TURN_FACTOR": tf,
            "CRAZYCAR_REBOUND_TURN_OFFSET": to,
        },
    })

# sort ascending score
results.sort(key=lambda r: r["score"])

print(f"Scanned {count} combinations. Top 5 parameter sets (lower score is better):\n")
for i, r in enumerate(results[:5], start=1):
    p = r["params"]
    print(f"{i}. score={r['score']:.3f} new_speed={r['new_speed']:.3f} pos_delta={r['pos_mag']:.3f} turn={r['turn_mag']:.2f}")
    for k, v in p.items():
        print(f"    {k} = {v}")
    print()

print("Recommendation: pick one of the above and set them in your environment before starting the sim.")
print("Example (PowerShell):")
print("$env:CRAZYCAR_REBOUND_DAMP_SMALL = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_DAMP_SMALL'])
print("$env:CRAZYCAR_REBOUND_DAMP_MED = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_DAMP_MED'])
print("$env:CRAZYCAR_REBOUND_DAMP_LARGE = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_DAMP_LARGE'])
print("$env:CRAZYCAR_REBOUND_K0 = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_K0'])
print("$env:CRAZYCAR_REBOUND_S_FACTOR = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_S_FACTOR'])
print("$env:CRAZYCAR_REBOUND_TURN_FACTOR = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_TURN_FACTOR'])
print("$env:CRAZYCAR_REBOUND_TURN_OFFSET = \"%s\"" % results[0]['params']['CRAZYCAR_REBOUND_TURN_OFFSET'])
