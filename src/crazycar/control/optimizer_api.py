# src/crazycar/control/optimizer_api.py
from __future__ import annotations
"""
Öffentliche Optimizer-API:
- simulate_car: schreibt Regler-Parameter, startet Simulation im Child, wartet bis time_limit
- run_optimization: ruft SciPy 'minimize' mit _objective_function

Neu:
- ESC-Abbruch: Das Child meldet 'aborted' via Queue → Elternprozess wirft KeyboardInterrupt
- Robuster Prozess-Lifecycle über optimizer_workers (spawn, cleanup)
- Detaillierte Logs (Konfiguration der Handler/Level bleibt Aufgabe von main.py)
"""

import logging
import time
import multiprocessing as mp
import queue as _queue
from typing import Dict, Optional

from scipy.optimize import minimize

from .optimizer_workers import (
    spawn_worker,
    cleanup_worker,
    make_queue,  # Queue aus 'spawn'-Kontext
)
from .optimizer_adapter import (
    update_parameters_in_interface,
    run_neat_simulation,   # Fallback-Entry (ohne Queue)
    log_path,
)

# Optionaler Entry mit Status-Signalen (ok/aborted/error); wenn nicht vorhanden → Fallback
try:
    from .optimizer_adapter import run_neat_entry  # type: ignore
except Exception:
    run_neat_entry = None  # type: ignore

__all__ = ["simulate_car", "run_optimization"]

log = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Öffentliche API: Simulation mit Zeitlimit (+ ESC-Abbruch aus Child)
# -----------------------------------------------------------------------------
def simulate_car(
    k1: float,
    k2: float,
    k3: float,
    kp1: float,
    kp2: float,
    time_limit: int = 60,
    pop_size: int = 2,
) -> float:
    """
    Führt die Simulation mit Zeitlimit aus und gibt eine „Rundenzeit“ zurück.
    Semantik wie zuvor: erst werden die Parameter in interface.py geschrieben.
    NEU: Wenn das Child 'aborted' meldet (ESC), wird KeyboardInterrupt geworfen,
         damit die Optimierung sauber beendet.
    """
    # 1) Parameter persistieren (bewusst altes Verhalten)
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)
    log.debug(
        "Parameters written: k1=%.3f k2=%.3f k3=%.3f kp1=%.3f kp2=%.3f pop=%d",
        k1, k2, k3, kp1, kp2, pop_size
    )

    # 2) EntryPoint bestimmen
    child_entry = run_neat_entry if run_neat_entry else run_neat_simulation

    # 3) Queue für Statusmeldungen (nur von run_neat_entry genutzt)
    q = make_queue()

    # 4) Child starten
    if child_entry is run_neat_simulation:
        args = (k1, k2, k3, kp1, kp2, pop_size)
    else:
        args = (q, k1, k2, k3, kp1, kp2, pop_size)

    p = spawn_worker(child_entry, args=args, kwargs={}, daemon=True)  # type: ignore[arg-type]

    # 5) Warten bis time_limit, dabei Queue poll’n
    start = time.time()
    deadline = start + max(0.0, float(time_limit))
    aborted = False
    finished_ok = False
    runtime: Optional[float] = None

    log.info("Simulation gestartet (pid=%s, time_limit=%ss)", getattr(p, "pid", None), time_limit)

    while time.time() < deadline:
        if not p.is_alive():
            # Prozess ist beendet → letzte Message (falls vorhanden) lesen
            msg = _try_get(q)
            handled, aborted, finished_ok, runtime = _apply_status_message(msg, aborted, finished_ok, runtime)
            break

        # Nicht-blockierende Statusprüfung
        msg = _try_get(q)
        handled, aborted, finished_ok, runtime = _apply_status_message(msg, aborted, finished_ok, runtime)
        if handled:
            break

        time.sleep(0.05)

    # 6) Cleanup (terminate → join → ggf. Hard-Kill)
    cleanup_worker(p)

    # 7) Laufzeit & Logging
    lap_time = time.time() - start
    log.info("Simulation beendet: lap_time=%.3fs aborted=%s finished_ok=%s", lap_time, aborted, finished_ok)

    if lap_time >= 20:
        try:
            with open(log_path(), encoding="utf-8", mode="a+") as f:
                f.write("20\n")
        except Exception as e:
            log.debug("Schreiben in log.csv fehlgeschlagen: %r", e)

    # 8) ESC → Optimierung abbrechen
    if aborted:
        raise KeyboardInterrupt("Simulation aborted via ESC")

    # 9) bevorzugt: echte Runtime vom Child (genauer als lap_time)
    if finished_ok and runtime is not None:
        return float(runtime)

    # 10) Fallback
    return lap_time


def _try_get(q):
    """Nicht-blockierender Queue-Read; gibt dict|None."""
    try:
        return q.get_nowait()
    except _queue.Empty:
        return None
    except Exception as e:
        log.debug("Queue read ignored error: %r", e)
        return None


def _apply_status_message(msg, aborted: bool, finished_ok: bool, runtime: Optional[float]):
    """
    Interpretiert eine Child-Status-Message.
    Erwartet:
      {"status": "ok", "runtime": <float>}
      {"status": "aborted"}
      {"status": "error", "error": "...repr..."}
    Gibt (handled, aborted, finished_ok, runtime) zurück.
    """
    if not msg or not isinstance(msg, dict):
        return False, aborted, finished_ok, runtime

    st = msg.get("status")
    if st == "ok":
        runtime = float(msg.get("runtime", 0.0))
        finished_ok = True
        log.debug("Child meldet OK: runtime=%.3fs", runtime)
        return True, aborted, finished_ok, runtime

    if st == "aborted":
        aborted = True
        log.info("Child meldet Abbruch (ESC).")
        return True, aborted, finished_ok, runtime

    if st == "error":
        err = msg.get("error")
        log.error("Child meldet Fehler: %s", err)
        raise RuntimeError(f"Simulation error (child): {err}")

    # Unbekannt → ignorieren
    log.debug("Unbekannte Child-Message: %r", msg)
    return False, aborted, finished_ok, runtime


# -----------------------------------------------------------------------------
# Minimizer-Zielfunktion & Einstiegspunkt
# -----------------------------------------------------------------------------
def _objective_function(params):
    k1, k2, k3, kp1, kp2 = params
    # Negieren, weil minimize() minimiert – so maximieren wir implizit die Laufzeit/Score
    val = -simulate_car(k1, k2, k3, kp1, kp2)
    log.debug("Objective(params=%s) -> %s", params, val)
    return val


def run_optimization(
    initial_point=None,
    bounds=None,
    method: str = "L-BFGS-B",
) -> Dict[str, float | bool | str]:
    """
    Öffentlicher Einstiegspunkt (z. B. von main.py).
    - schreibt log.csv-Header
    - fängt KeyboardInterrupt ab (ESC in der Simulation) und liefert sauberes Ergebnis
    """
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20.0)] * 5

    try:
        with open(log_path(), encoding="utf-8", mode="w") as f:
            f.write("Parameter,round_time\n")
    except Exception as e:
        log.debug("Konnte log.csv nicht initialisieren: %r", e)

    log.info("Starte Optimierung: method=%s initial=%s", method, initial_point)

    try:
        result = minimize(_objective_function, initial_point, method=method, bounds=bounds)
        optimal_k1, optimal_k2, optimal_k3, optimal_kp1, optimal_kp2 = result.x
        optimal_lap_time = -result.fun

        out = {
            "k1": float(optimal_k1),
            "k2": float(optimal_k2),
            "k3": float(optimal_k3),
            "kp1": float(optimal_kp1),
            "kp2": float(optimal_kp2),
            "optimal_lap_time": float(optimal_lap_time),
            "success": bool(result.success),
            "message": str(result.message),
        }
        log.info("Optimierung fertig: success=%s message=%s", out["success"], out["message"])
        return out

    except KeyboardInterrupt:
        # ESC im Child → sauberer Abbruch
        log.warning("Optimierung abgebrochen (ESC in Simulation).")
        return {"success": False, "message": "Abgebrochen (ESC in der Simulation)"}
