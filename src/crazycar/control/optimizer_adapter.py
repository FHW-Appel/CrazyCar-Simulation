"""Optimizer Adapter - Parameter Injection + Simulation Launcher.

This module sits between parameter-tuning code and the simulation.

What it does:
- Provides path helpers (interface.py, log.csv, optional NEAT config)
- Updates tuning parameters (k1/k2/k3/kp1/kp2) by rewriting
    `control/interface.py` (historic behavior retained)
- Launches the simulation in a way that works well in child processes
    (status reporting: ok/aborted/error)

Default behavior (important):
- The project is configured to run in "DLL-only" mode by default
    (`DLL_ONLY_DEFAULT = 1`).
- In DLL-only mode, NEAT is skipped entirely and a direct simulation entry
    point is called (e.g. run_direct/run_loop/main).
    This supports the primary use-case: testing the native student controller
    built from the C sources.

Optional behavior:
- If DLL-only is disabled (`DLL_ONLY_DEFAULT = 0` and no overriding env var),
    this module can run a NEAT-based evaluator using config_neat.txt.

Notes:
- Parameter keys: k1, k2, k3, kp1, kp2
- Env override: CRAZYCAR_ONLY_DLL=1/true/yes/on forces DLL-only.
"""
# src/crazycar/control/optimizer_adapter.py
import logging
import os
import time
import inspect
from importlib import import_module
from typing import Any, List, Callable, Optional

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# GLOBAL SWITCH (Code)
# 0 = Use NEAT normally
# 1 = DLL-only (NEAT completely skipped; direct simulation)
# -----------------------------------------------------------------------------
DLL_ONLY_DEFAULT: int = 1  # <<— always use DLL logic

# Retained keys (controller parameters)
_DLL_PARAMETER_KEYS: List[str] = ["k1", "k2", "k3", "kp1", "kp2"]

__all__ = [
    "_DLL_PARAMETER_KEYS",
    "here",
    "neat_config_path",
    "interface_py_path",
    "log_path",
    "update_parameters_in_interface",
    "run_neat_simulation",
    "run_neat_entry",
]


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
def here() -> str:
    """Folder of this module: .../src/crazycar/control/"""
    return os.path.dirname(__file__)


def neat_config_path() -> str:
    """Path to NEAT config (in same folder as this file)."""
    return os.path.abspath(os.path.join(here(), "config_neat.txt"))


def interface_py_path() -> str:
    """Path to controller file where parameters (k1..kp2) are written."""
    return os.path.abspath(os.path.join(here(), "interface.py"))


def log_path() -> str:
    """Path to log file (log.csv) in this folder."""
    return os.path.abspath(os.path.join(here(), "log.csv"))


# ---------------------------------------------------------------------------
# Internal switch: "DLL/Simulation only" active?
# - Env var CRAZYCAR_ONLY_DLL overrides code switch.
# ---------------------------------------------------------------------------
def _dll_only_mode() -> bool:
    """
    Returns True if CRAZYCAR_ONLY_DLL is set (1/true/yes/on) OR the code switch is active.
    """
    v = os.getenv("CRAZYCAR_ONLY_DLL", "")
    if v in ("1", "true", "True", "yes", "on"):
        return True
    return bool(int(DLL_ONLY_DEFAULT))


# ---------------------------------------------------------------------------
# Parameter in control/interface.py schreiben (altes Verhalten, nur ausgelagert)
# ---------------------------------------------------------------------------
def update_parameters_in_interface(k1: float, k2: float, k3: float, kp1: float, kp2: float) -> None:
    """
    Writes k1..kp2 into control/interface.py (text rewrite of corresponding lines).
    Caution: This method is fragile but deliberately retained.
    """
    path = interface_py_path()
    
    # Capture parameters for logging before dict comprehension scope issues
    params = locals().copy()

    with open(path, encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    replaced = set()
    for key in _DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
                # params contains k1..kp2 – access dynamically:
                lines[i] = f"{indent}{parts[0].strip()} = {params[key]}\n"
                replaced.add(key)
                break

    missing = [k for k in _DLL_PARAMETER_KEYS if k not in replaced]
    if missing:
        log.warning("Parameters not found in interface.py → not replaced: %s", missing)

    with open(path, encoding="utf-8", mode="w") as f:
        f.writelines(lines)

    log.debug("interface.py updated: %s", {k: params[k] for k in _DLL_PARAMETER_KEYS})


# ---------------------------------------------------------------------------
# Direct simulation call (DLL-only): dynamically find entry & start
# ---------------------------------------------------------------------------
_CANDIDATE_MODULES: list[tuple[str, list[str]]] = [
    # (Module, possible function names in order)
    ("crazycar.sim.loop",        ["run_loop", "run", "main"]),
    ("crazycar.sim.simulation",  ["run_direct", "run_game", "main"]),
    ("crazycar.sim",             ["run_direct", "run_loop", "run", "main"]),
]

def _find_direct_entry() -> tuple[Callable[..., Any], Optional[dict]]:
    """Find direct simulation entry point (without NEAT signature).
    
    Searches candidate modules for callable entry points.
    
    Returns:
        Tuple (callable, default_kwargs) or raises RuntimeError with hints
        
    Raises:
        RuntimeError: If no suitable entry point found
    """
    for mod_name, fn_names in _CANDIDATE_MODULES:
        try:
            mod = import_module(mod_name)
        except Exception:
            continue

        for fn_name in fn_names:
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                # Inspect signature and potentially offer harmless defaults
                try:
                    sig = inspect.signature(fn)
                except Exception:
                    # Call blind if needed
                    return fn, None

                # Support optional duration parameters but don't force anything
                kwargs: dict | None = {}
                params = sig.parameters
                # Only populate optional, harmless parameters
                if "duration" in params and params["duration"].default is not inspect._empty:
                    kwargs["duration"] = params["duration"].default
                elif "duration_s" in params and params["duration_s"].default is not inspect._empty:
                    kwargs["duration_s"] = params["duration_s"].default
                elif "max_seconds" in params and params["max_seconds"].default is not inspect._empty:
                    kwargs["max_seconds"] = params["max_seconds"].default
                else:
                    # If all parameters optional or none: leave kwargs empty
                    # If required parameters exist that we don't know → next candidate
                    required = [p for p in params.values()
                                if p.default is inspect._empty
                                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                    if required:
                        # E.g., NEAT variant (genomes, config) → skip
                        continue

                return fn, (kwargs or None)

    raise RuntimeError(
        "No direct simulation entry found. "
        "Please export e.g. `run_direct()` in crazycar.sim.simulation or "
        "`run_loop()` in crazycar.sim.loop (without NEAT parameters)."
    )


def _run_direct_simulation() -> float:
    """
    Start simulation without NEAT via direct entry point.
    Measures and returns runtime in seconds (for reference only).
    """
    entry, kwargs = _find_direct_entry()
    log.info("DLL-Only mode active → starting direct simulation without NEAT: %s.%s",
             entry.__module__, getattr(entry, "__name__", "<callable>"))

    start = time.time()
    # Tolerant call: with/without kwargs
    if kwargs:
        entry(**kwargs)
    else:
        entry()
    end = time.time()

    runtime = end - start
    log.info("Direct simulation (DLL-Only) complete: runtime=%.3fs", runtime)
    return runtime


# ---------------------------------------------------------------------------
# NEAT simulation (to be called in child process) – with DLL-only bypass
# ---------------------------------------------------------------------------
def run_neat_simulation(
    k1: float,
    k2: float,
    k3: float,
    kp1: float,
    kp2: float,
    pop_size: int = 2,
) -> float:
    """
    Starts NEAT-based simulation and returns runtime in seconds.
    DLL-only active? → NEAT skipped, direct sim entry used.
    """
    # ---- DLL-ONLY-BYPASS ---------------------------------------------------
    if _dll_only_mode():
        # (optional) Log parameters – retain old behavior
        try:
            with open(log_path(), encoding="utf-8", mode="a+") as f:
                f.write(str([k1, k2, k3, kp1, kp2]) + ",")
        except Exception as e:
            log.debug("Could not open log.csv for parameter append (DLL-only): %r", e)

        return _run_direct_simulation()
    # -----------------------------------------------------------------------

    # Lazy import of NEAT (only if NOT in DLL-only mode)
    from neat.config import Config as NeatConfig
    from neat.genome import DefaultGenome
    from neat.reproduction import DefaultReproduction
    from neat.species import DefaultSpeciesSet
    from neat.stagnation import DefaultStagnation
    from neat.population import Population
    from neat.reporting import StdOutReporter
    from neat.statistics import StatisticsReporter

    # Lazy import of simulation (NEAT evaluator)
    from crazycar.sim.simulation import run_simulation

    cfg_path = neat_config_path()
    config = NeatConfig(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        cfg_path,
    )

    # Optional: Override pop_size from parameters (if smaller in config)
    if isinstance(pop_size, int) and pop_size > 0:
        try:
            config.pop_size = pop_size
        except Exception:
            pass  # Different NEAT versions encapsulate pop_size differently

    # (optional) Log parameters – old behavior
    try:
        with open(log_path(), encoding="utf-8", mode="a+") as f:
            f.write(str([k1, k2, k3, kp1, kp2]) + ",")
    except Exception as e:
        log.debug("Could not open log.csv for parameter append: %r", e)

    population = Population(config)
    population.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    population.add_reporter(stats)

    log.info(
        "Starting NEAT simulation: pop_size=%s config=%s",
        getattr(config, "pop_size", "?"),
        cfg_path,
    )

    start = time.time()
    # Caution: run_simulation is the NEAT evaluator (genomes, config)
    population.run(run_simulation, 1000)
    end = time.time()

    runtime = end - start
    log.info("NEAT simulation complete: runtime=%.3fs", runtime)
    return runtime


# ---------------------------------------------------------------------------
# Child entry with status communication (for ESC abort)
# ---------------------------------------------------------------------------
def _queue_close_safe(q: Any) -> None:
    """Close child-side of queue robustly to ensure messages are flushed."""
    try:
        if hasattr(q, "close"):
            q.close()
        if hasattr(q, "join_thread"):
            q.join_thread()
    except Exception:
        pass


def run_neat_entry(queue: Any, k1: float, k2: float, k3: float, kp1: float, kp2: float, pop_size: int = 2) -> None:
    """
    Wrapper around run_neat_simulation that sends status to parent process:
      - {"status": "ok",      "runtime": <float>}
      - {"status": "aborted"} (on ESC/SystemExit/KeyboardInterrupt)
      - {"status": "error",   "error": "...repr..."}
    """
    try:
        runtime = run_neat_simulation(k1, k2, k3, kp1, kp2, pop_size=pop_size)
        try:
            queue.put({"status": "ok", "runtime": float(runtime)})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)  # win/spawn: Let feeder flush
        return

    except (KeyboardInterrupt, SystemExit):
        try:
            queue.put({"status": "aborted"})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)
        return

    except Exception as e:
        try:
            queue.put({"status": "error", "error": repr(e)})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)
        return
