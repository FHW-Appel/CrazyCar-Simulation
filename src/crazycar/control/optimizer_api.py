"""Optimizer Public API - SciPy-based parameter optimization.

Responsibilities:
- High-level optimization API for controller parameters
- Multiprocessing child process management
- Time-limited simulations with ESC abort handling
- Integration with SciPy optimize.minimize

Public API:
- simulate_car(
      k1, k2, k3, kp1, kp2,
      time_limit: int = 60,
      pop_size: int = 2
  ) -> float:
      Run one simulation with given parameters
      Returns lap time (lower is better)
      Raises KeyboardInterrupt if user aborts (ESC)
      
- run_optimization(
      initial_params: dict,
      method: str = 'Nelder-Mead',
      **kwargs
  ) -> OptimizeResult:
      Run SciPy optimization to find best parameters
      Searches parameter space to minimize lap time

Usage:
    # Single simulation test
    lap_time = simulate_car(k1=1.0, k2=0.5, k3=0.2, kp1=0.8, kp2=0.3)
    
    # Full optimization
    initial = {'k1': 1.0, 'k2': 0.5, 'k3': 0.2, 'kp1': 0.8, 'kp2': 0.3}
    result = run_optimization(initial, method='Nelder-Mead')
    print("Best parameters:", result.x)

Notes:
- Uses 'spawn' multiprocessing context (Windows-safe)
- Child processes communicate via Queue (status/abort/error)
- ESC in child raises KeyboardInterrupt in parent
- Cleans up child processes on exit
- Integrates with optimizer_adapter for parameter injection
- Logs to 'control/log.csv' for analysis
"""
# src/crazycar/control/optimizer_api.py
import time
import logging
import multiprocessing as mp
import queue as _queue
from typing import Dict, Optional

from scipy.optimize import minimize

from .optimizer_workers import (
    spawn_worker,
    cleanup_worker,
    make_queue,  # Queue from 'spawn' context
)
from .optimizer_adapter import (
    update_parameters_in_interface,
    run_neat_simulation,   # Fallback-Entry (ohne Queue)
    log_path,
)

# Optional entry with status signals (ok/aborted/error); if not available → fallback
try:
    from .optimizer_adapter import run_neat_entry  # type: ignore
except Exception:
    run_neat_entry = None  # type: ignore

__all__ = ["simulate_car", "run_optimization"]

log = logging.getLogger(__name__)

# Polling interval for child process queue (seconds)
QUEUE_POLL_INTERVAL = 0.1  # Check every 100ms


# -----------------------------------------------------------------------------
# Public API: Time-Limited Simulation (+ ESC Abort from Child Process)
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
    """Run simulation with time limit and return lap time.
    
    Parameters are first written to interface.py, then simulation starts
    in a child process with status communication via Queue. If child reports
    'aborted' (ESC pressed), raises KeyboardInterrupt to cleanly terminate
    optimization.
    
    Args:
        k1: Controller parameter 1
        k2: Controller parameter 2
        k3: Controller parameter 3
        kp1: Proportional gain parameter 1
        kp2: Proportional gain parameter 2
        time_limit: Maximum runtime in seconds. Default: 60
        pop_size: NEAT population size. Default: 2
        
    Returns:
        Lap time in seconds (lower is better)
        
    Raises:
        KeyboardInterrupt: If user aborts with ESC in child process
        
    Note:
        Writes parameters to interface.py, spawns child process,
        and logs to control/log.csv.
    """
    # 1) Persist parameters (deliberately old behavior)
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)
    log.debug(
        "Parameters written: k1=%.3f k2=%.3f k3=%.3f kp1=%.3f kp2=%.3f pop=%d",
        k1, k2, k3, kp1, kp2, pop_size
    )

    # 2) Determine entry point
    child_entry = run_neat_entry if run_neat_entry else run_neat_simulation

    # 3) Queue for status messages (only used by run_neat_entry)
    q = make_queue()

    # 4) Start child process
    if child_entry is run_neat_simulation:
        args = (k1, k2, k3, kp1, kp2, pop_size)
    else:
        args = (q, k1, k2, k3, kp1, kp2, pop_size)

    p = spawn_worker(child_entry, args=args, kwargs={}, daemon=True)  # type: ignore[arg-type]

    # 5) Wait until time_limit, polling queue
    start = time.time()
    deadline = start + max(0.0, float(time_limit))
    aborted = False
    finished_ok = False
    runtime: Optional[float] = None

    log.info("Simulation started (pid=%s, time_limit=%ss)", getattr(p, "pid", None), time_limit)

    while time.time() < deadline:
        if not p.is_alive():
            # Process terminated → read last message (if available)
            msg = _try_get(q)
            handled, aborted, finished_ok, runtime = _apply_status_message(msg, aborted, finished_ok, runtime)
            break

        # Non-blocking status check
        msg = _try_get(q)
        handled, aborted, finished_ok, runtime = _apply_status_message(msg, aborted, finished_ok, runtime)
        if handled:
            break

        time.sleep(QUEUE_POLL_INTERVAL)

    # 6) Cleanup: Terminate process (terminate → join → if needed kill)
    cleanup_worker(p)

    # 7) Calculate and log runtime
    lap_time = time.time() - start
    log.info("Simulation ended: lap_time=%.3fs aborted=%s finished_ok=%s", lap_time, aborted, finished_ok)

    # Legacy: Write long runs to log.csv (>= 20 seconds)
    LOG_THRESHOLD_SECONDS = 20
    if lap_time >= LOG_THRESHOLD_SECONDS:
        try:
            with open(log_path(), encoding="utf-8", mode="a+") as f:
                f.write("20\n")
        except Exception as e:
            log.debug("Writing to log.csv failed: %r", e)

    # 8) ESC abort → stop optimization
    if aborted:
        raise KeyboardInterrupt("Simulation aborted via ESC")

    # 9) Preferred: Real runtime from child (more precise than lap_time)
    if finished_ok and runtime is not None:
        return float(runtime)

    # 10) Fallback: Wall-Clock-Zeit
    return lap_time


def _try_get(q):
    """Non-blocking queue read, returns dict or None.
    
    Args:
        q: multiprocessing.Queue instance
        
    Returns:
        Dict from queue if available, None otherwise.
    """
    try:
        return q.get_nowait()
    except _queue.Empty:
        return None
    except Exception as e:
        log.debug("Queue read ignored error: %r", e)
        return None


def _apply_status_message(msg, aborted: bool, finished_ok: bool, runtime: Optional[float]):
    """Interpret child process status message.
    
    Processes status messages from child:
    - {"status": "ok", "runtime": <float>} → Success
    - {"status": "aborted"} → ESC pressed
    - {"status": "error", "error": "..."} → Exception
    
    Args:
        msg: Dict from child process queue
        aborted: Current abort flag
        finished_ok: Current success flag
        runtime: Current runtime value
        
    Returns:
        Tuple (handled, aborted, finished_ok, runtime):
        - handled: True if message was recognized
        - aborted: Updated abort flag
        - finished_ok: Updated success flag
        - runtime: Updated runtime (seconds)
        
    Raises:
        RuntimeError: If child reports error status
    """
    if not msg or not isinstance(msg, dict):
        return False, aborted, finished_ok, runtime

    st = msg.get("status")
    if st == "ok":
        runtime = float(msg.get("runtime", 0.0))
        finished_ok = True
        log.debug("Child reports OK: runtime=%.3fs", runtime)
        return True, aborted, finished_ok, runtime

    if st == "aborted":
        aborted = True
        log.info("Child reports abort (ESC).")
        return True, aborted, finished_ok, runtime

    if st == "error":
        err = msg.get("error")
        log.error("Child reports error: %s", err)
        raise RuntimeError(f"Simulation error (child): {err}")

    # Unknown → ignore
    log.debug("Unknown child message: %r", msg)
    return False, aborted, finished_ok, runtime


# -----------------------------------------------------------------------------
# Objective function for SciPy minimize
# -----------------------------------------------------------------------------
def _objective_function(params):
    """Objective function for SciPy minimize.
    
    Evaluates one parameter set by running simulation and negates result
    because minimize() minimizes (we want to maximize runtime/score).
    
    Args:
        params: Array [k1, k2, k3, kp1, kp2]
        
    Returns:
        Negated lap time (for minimization)
    """
    k1, k2, k3, kp1, kp2 = params
    val = -simulate_car(k1, k2, k3, kp1, kp2)
    log.debug("Objective(params=%s) -> %s", params, val)
    return val


def run_optimization(
    initial_point=None,
    bounds=None,
    method: str = "L-BFGS-B",
) -> Dict[str, float | bool | str]:
    """Run SciPy optimization to find best controller parameters.
    
    Initializes log.csv with header, runs SciPy minimize, and catches
    KeyboardInterrupt (ESC in simulation) for clean abort.
    
    Args:
        initial_point: Starting parameter values [k1, k2, k3, kp1, kp2].
            Default: [1.1, 1.1, 1.1, 1.0, 1.0]
        bounds: Parameter bounds [(min, max), ...].
            Default: [(1.1, 20.0)] * 5
        method: SciPy optimization method. Default: "L-BFGS-B"
        
    Returns:
        Dict with optimization result:
            - 'success': bool - Whether optimization succeeded
            - 'message': str - Status message
            - 'k1', 'k2', 'k3', 'kp1', 'kp2': float - Optimal parameters
            - 'optimal_lap_time': float - Best lap time achieved
            
    Note:
        Writes to control/log.csv and spawns multiple child processes.
        Returns {"success": False} if user aborts with ESC.
    """
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20.0)] * 5

    try:
        with open(log_path(), encoding="utf-8", mode="w") as f:
            f.write("Parameter,round_time\n")
    except Exception as e:
        log.debug("Could not initialize log.csv: %r", e)

    log.info("Starting optimization: method=%s initial=%s", method, initial_point)

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
        log.info("Optimization complete: success=%s message=%s", out["success"], out["message"])
        return out

    except KeyboardInterrupt:
        # ESC in child → clean abort
        log.warning("Optimization aborted (ESC in simulation).")
        return {"success": False, "message": "Aborted (ESC in simulation)"}
