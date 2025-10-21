# src/crazycar/control/optimizer_adapter.py
from __future__ import annotations
"""
Adapter-Schicht zwischen Optimizer und Simulation/NEAT.

Aufgaben:
- Pfad-Helfer für config/interface/log
- Parameter in control/interface.py schreiben (Beibehaltung des alten Verhaltens)
- NEAT-Simulation starten (lazy imports → Tests & Start schneller)
- Child-Entry 'run_neat_entry' mit Statuskommunikation via Queue (ESC/Fehler/OK)
"""

import logging
import os
import time
from typing import Any, List

log = logging.getLogger(__name__)

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
    # locals() enthält k1..kp2 – damit greifen wir dynamisch auf den passenden Wert zu
    for key in _DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
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
# NEAT-Simulation (im Child-Prozess aufzurufen)
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
    Lazy-Imports → schneller Start & weniger harte Abhängigkeiten in Tests.
    """
    # Lazy-Import von NEAT
    from neat.config import Config as NeatConfig
    from neat.genome import DefaultGenome
    from neat.reproduction import DefaultReproduction
    from neat.species import DefaultSpeciesSet
    from neat.stagnation import DefaultStagnation
    from neat.population import Population
    from neat.reporting import StdOutReporter
    from neat.statistics import StatisticsReporter

    # Lazy-Import der Simulation
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
            pass  # unterschiedliche NEAT-Versionen kapseln pop_size unterschiedlich

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

    log.info("NEAT-Simulation startet: pop_size=%s config=%s", getattr(config, "pop_size", "?"), cfg_path)

    start = time.time()
    # Achtung: run_simulation kann intern ESC → pygame.quit() → sys.exit(0) auslösen
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
        # mp.Queue auf Windows hat close/join_thread
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
    WICHTIG: KEIN os._exit() → sonst gehen Queue-Messages verloren. Sauber returnen!
    """
    try:
        runtime = run_neat_simulation(k1, k2, k3, kp1, kp2, pop_size=pop_size)
        try:
            queue.put({"status": "ok", "runtime": float(runtime)})
        finally:
            _queue_close_safe(queue)
            # win/spawn: kurzen Moment geben, damit der Feeder flushen kann
            time.sleep(0.02)
        return  # sauberer Child-Exit

    except (KeyboardInterrupt, SystemExit):
        try:
            queue.put({"status": "aborted"})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)
        return  # sauberer Child-Exit

    except Exception as e:
        try:
            queue.put({"status": "error", "error": repr(e)})
        finally:
            _queue_close_safe(queue)
            time.sleep(0.02)
        return  # sauberer Child-Exit
