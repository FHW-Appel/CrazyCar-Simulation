# src/crazycar/control/optimizer_adapter.py
from __future__ import annotations
"""
Adapter-Schicht zwischen Optimizer und Simulation/NEAT.

Aufgaben:
- Pfad-Helfer für config/interface/log
- Parameter in control/interface.py schreiben (Beibehaltung des alten Verhaltens)
- NEAT-Simulation starten (lazy imports → Tests & Start schneller)
- Child-Entry 'run_neat_entry' mit Statuskommunikation via Queue (ESC/Fehler/OK)

NEU:
- Fester DLL-Only-Schalter (DLL_ONLY_DEFAULT = 1) → NEAT wird standardmäßig übersprungen.
- Im DLL-Only-Modus wird automatisch ein DIREKTER Sim-Entry gesucht (run_direct/run_loop/run_game/main),
  per Reflection aufrufbar gemacht und gestartet. So testest du die C-DLL (myFunktions.c → fahren1()) ohne NEAT.
"""

import logging
import os
import time
import inspect
from importlib import import_module
from typing import Any, List, Callable, Optional

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# GLOBALER SCHALTER (Code)
# 0 = NEAT normal verwenden
# 1 = DLL-only (NEAT wird komplett übersprungen; direkte Simulation)
# -----------------------------------------------------------------------------
DLL_ONLY_DEFAULT: int = 1  # <<— immer DLL-Logik nutzen

# Beibehaltene Schlüssel (Regler-Parameter)
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
# Pfad-Helfer
# ---------------------------------------------------------------------------
def here() -> str:
    """Ordner dieses Moduls: .../src/crazycar/control/"""
    return os.path.dirname(__file__)


def neat_config_path() -> str:
    """Pfad zu NEAT-Config (liegt im gleichen Ordner wie dieses File)."""
    return os.path.abspath(os.path.join(here(), "config_neat.txt"))


def interface_py_path() -> str:
    """Pfad zur Controller-Datei, in die die Parameter (k1..kp2) geschrieben werden."""
    return os.path.abspath(os.path.join(here(), "interface.py"))


def log_path() -> str:
    """Pfad zur Log-Datei (log.csv) in diesem Ordner."""
    return os.path.abspath(os.path.join(here(), "log.csv"))


# ---------------------------------------------------------------------------
# Interner Umschalter: „Nur DLL/Simulation“ aktiv?
# - Env-Var CRAZYCAR_ONLY_DLL überschreibt den Code-Schalter.
# ---------------------------------------------------------------------------
def _dll_only_mode() -> bool:
    """
    True, wenn CRAZYCAR_ONLY_DLL gesetzt ist (1/true/yes/on) ODER der Code-Schalter aktiv ist.
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
    Schreibt k1..kp2 in control/interface.py (Text-Rewrite der entsprechenden Zeilen).
    Achtung: Dieses Verfahren ist fragil, wird aber bewusst beibehalten.
    """
    path = interface_py_path()

    with open(path, encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    replaced = set()
    for key in _DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
                # locals() enthält k1..kp2 – so greifen wir dynamisch zu:
                lines[i] = f"{indent}{parts[0].strip()} = {locals()[key]}\n"
                replaced.add(key)
                break

    missing = [k for k in _DLL_PARAMETER_KEYS if k not in replaced]
    if missing:
        log.warning("Parameter in interface.py nicht gefunden → nicht ersetzt: %s", missing)

    with open(path, encoding="utf-8", mode="w") as f:
        f.writelines(lines)

    log.debug("interface.py aktualisiert: %s", {k: locals()[k] for k in _DLL_PARAMETER_KEYS})


# ---------------------------------------------------------------------------
# Direkter Simulationsaufruf (DLL-only): dynamisch Einstieg finden & starten
# ---------------------------------------------------------------------------
_CANDIDATE_MODULES: list[tuple[str, list[str]]] = [
    # (Modul, mögliche Funktionsnamen in Reihenfolge)
    ("crazycar.sim.loop",        ["run_loop", "run", "main"]),
    ("crazycar.sim.simulation",  ["run_direct", "run_game", "main"]),
    ("crazycar.sim",             ["run_direct", "run_loop", "run", "main"]),
]

def _find_direct_entry() -> tuple[Callable[..., Any], Optional[dict]]:
    """
    Sucht einen direkten Sim-Entry (ohne NEAT-Signatur).
    Gibt (callable, default_kwargs) zurück oder wirft RuntimeError mit Hinweisen.
    """
    for mod_name, fn_names in _CANDIDATE_MODULES:
        try:
            mod = import_module(mod_name)
        except Exception:
            continue

        for fn_name in fn_names:
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                # Signatur inspizieren und evtl. harmlose Defaults anbieten
                try:
                    sig = inspect.signature(fn)
                except Exception:
                    # Zur Not blind aufrufen
                    return fn, None

                # Unterstütze optionale Dauer-Parameter, aber zwinge nichts auf
                kwargs: dict | None = {}
                params = sig.parameters
                # nur optionale, harmlose Parameter belegen
                if "duration" in params and params["duration"].default is not inspect._empty:
                    kwargs["duration"] = params["duration"].default
                elif "duration_s" in params and params["duration_s"].default is not inspect._empty:
                    kwargs["duration_s"] = params["duration_s"].default
                elif "max_seconds" in params and params["max_seconds"].default is not inspect._empty:
                    kwargs["max_seconds"] = params["max_seconds"].default
                else:
                    # Wenn alle Parameter optional oder gar keine: kwargs leer lassen
                    # Wenn Pflicht-Parameter existieren, die wir nicht kennen → nächster Kandidat
                    required = [p for p in params.values()
                                if p.default is inspect._empty
                                and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
                    if required:
                        # z. B. NEAT-Variante (genomes, config) → überspringen
                        continue

                return fn, (kwargs or None)

    raise RuntimeError(
        "Kein direkter Simulations-Einstieg gefunden. "
        "Bitte exportiere z. B. `run_direct()` in crazycar.sim.simulation oder "
        "`run_loop()` in crazycar.sim.loop (ohne NEAT-Parameter)."
    )


def _run_direct_simulation() -> float:
    """
    Startet die Simulation ohne NEAT über einen direkten Einstiegspunkt.
    Misst und liefert die Laufzeit in Sekunden (nur zur Orientierung).
    """
    entry, kwargs = _find_direct_entry()
    log.info("DLL-Only-Modus aktiv → starte direkte Simulation ohne NEAT: %s.%s",
             entry.__module__, getattr(entry, "__name__", "<callable>"))

    start = time.time()
    # Toleranter Aufruf: mit/ohne kwargs
    if kwargs:
        entry(**kwargs)
    else:
        entry()
    end = time.time()

    runtime = end - start
    log.info("Direkte Simulation (DLL-Only) fertig: runtime=%.3fs", runtime)
    return runtime


# ---------------------------------------------------------------------------
# NEAT-Simulation (im Child-Prozess aufzurufen) – mit DLL-Only-Bypass
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
    Startet eine NEAT-basierte Simulation und gibt die Laufzeit in Sekunden zurück.
    DLL-Only aktiv? → NEAT wird übersprungen, direkter Sim-Entry verwendet.
    """
    # ---- DLL-ONLY-BYPASS ---------------------------------------------------
    if _dll_only_mode():
        # (optional) Log der Parameter – altes Verhalten bleiben lassen
        try:
            with open(log_path(), encoding="utf-8", mode="a+") as f:
                f.write(str([k1, k2, k3, kp1, kp2]) + ",")
        except Exception as e:
            log.debug("Konnte log.csv nicht zum Parameter-Append öffnen (DLL-Only): %r", e)

        return _run_direct_simulation()
    # -----------------------------------------------------------------------

    # Lazy-Import von NEAT (nur wenn NICHT im DLL-Only-Modus)
    from neat.config import Config as NeatConfig
    from neat.genome import DefaultGenome
    from neat.reproduction import DefaultReproduction
    from neat.species import DefaultSpeciesSet
    from neat.stagnation import DefaultStagnation
    from neat.population import Population
    from neat.reporting import StdOutReporter
    from neat.statistics import StatisticsReporter

    # Lazy-Import der Simulation (NEAT-Evaluator)
    from crazycar.sim.simulation import run_simulation

    cfg_path = neat_config_path()
    config = NeatConfig(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        cfg_path,
    )

    # Optional: pop_size aus Parametern überschreiben (falls in der Config kleiner ist)
    if isinstance(pop_size, int) and pop_size > 0:
        try:
            config.pop_size = pop_size
        except Exception:
            pass  # verschiedene NEAT-Versionen kapseln pop_size unterschiedlich

    # (optional) Log der Parameter – altes Verhalten
    try:
        with open(log_path(), encoding="utf-8", mode="a+") as f:
            f.write(str([k1, k2, k3, kp1, kp2]) + ",")
    except Exception as e:
        log.debug("Konnte log.csv nicht zum Parameter-Append öffnen: %r", e)

    population = Population(config)
    population.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    population.add_reporter(stats)

    log.info(
        "NEAT-Simulation startet: pop_size=%s config=%s",
        getattr(config, "pop_size", "?"),
        cfg_path,
    )

    start = time.time()
    # Achtung: run_simulation ist hier der NEAT-Evaluator (genomes, config)
    population.run(run_simulation, 1000)
    end = time.time()

    runtime = end - start
    log.info("NEAT-Simulation fertig: runtime=%.3fs", runtime)
    return runtime


# ---------------------------------------------------------------------------
# Child-Entry mit Statuskommunikation (für ESC-Abbruch)
# ---------------------------------------------------------------------------
def _queue_close_safe(q: Any) -> None:
    """Schließt die Child-Seite der Queue robust, damit Messages sicher gespült werden."""
    try:
        if hasattr(q, "close"):
            q.close()
        if hasattr(q, "join_thread"):
            q.join_thread()
    except Exception:
        pass


def run_neat_entry(queue: Any, k1: float, k2: float, k3: float, kp1: float, kp2: float, pop_size: int = 2) -> None:
    """
    Wrapper um run_neat_simulation, der dem Elternprozess einen Status sendet:
      - {"status": "ok",      "runtime": <float>}
      - {"status": "aborted"} (bei ESC/SystemExit/KeyboardInterrupt)
      - {"status": "error",   "error": "...repr..."}
    """
    try:
        runtime = run_neat_simulation(k1, k2, k3, kp1, kp2, pop_size=pop_size)
        try:
            queue.put({"status": "ok", "runtime": float(runtime)})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)  # win/spawn: Feeder flushen lassen
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
