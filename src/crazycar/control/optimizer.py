# src/crazycar/control/optimizer.py
from __future__ import annotations

import os
import time
from multiprocessing import Process
from typing import Dict

from scipy.optimize import minimize

# NEAT – explizite Importe (pylance-freundlich)
from neat.config import Config as NeatConfig
from neat.genome import DefaultGenome
from neat.reproduction import DefaultReproduction
from neat.species import DefaultSpeciesSet
from neat.stagnation import DefaultStagnation
from neat.population import Population
from neat.reporting import StdOutReporter
from neat.statistics import StatisticsReporter

# Deine Simulation (jetzt sauber aus dem Paket importieren)
from crazycar.sim.simulation import run_simulation

# Welche Regler-Parameter wir optimieren (Beibehaltung des alten Verhaltens)
_DLL_PARAMETER_KEYS = ["k1", "k2", "k3", "kp1", "kp2"]


# ------------------------------------------------------------
# Pfad-Helfer
# ------------------------------------------------------------
def _here() -> str:
    return os.path.dirname(__file__)

def _neat_config_path() -> str:
    """
    NEU: config_neat.txt liegt jetzt IM GLEICHEN ORDNER wie dieses File (control/).
    """
    return os.path.abspath(os.path.join(_here(), "config_neat.txt"))

def _interface_py_path() -> str:
    """
    Pfad zur Controller-Datei, in die (wie vorher) die Parameter geschrieben werden.
    (Beibehaltung des bestehenden Verhaltens – fachlich nichts geändert.)
    """
    return os.path.abspath(os.path.join(_here(), "interface.py"))

def _log_path() -> str:
    return os.path.abspath(os.path.join(_here(), "log.csv"))


# ------------------------------------------------------------
# Parameter in control/interface.py schreiben (wie vorher)
# ------------------------------------------------------------
def _update_parameters_in_interface(k1: float, k2: float, k3: float, kp1: float, kp2: float) -> None:
    """
    Schreibt die Parameter-Werte in control/interface.py (Text-Rewrite).
    Hinweis: Das ist 1:1 das (fragile) alte Verhalten – bewusst beibehalten.
    """
    interface_path = _interface_py_path()

    with open(interface_path, encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    # locals() enthält k1..kp2
    for key in _DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            if line.strip().startswith(key):
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
                lines[i] = f"{indent}{parts[0].strip()} = {locals()[key]}\n"
                break

    with open(interface_path, encoding="utf-8", mode="w") as f:
        f.writelines(lines)


# ------------------------------------------------------------
# NEAT-Simulation (separate Funktion, damit wir sie im Process aufrufen können)
# ------------------------------------------------------------
def _run_neat_simulation(
    k1: float,
    k2: float,
    k3: float,
    kp1: float,
    kp2: float,
    pop_size: int = 2,
) -> float:
    """
    Startet eine NEAT-basierte Simulation und gibt die Laufzeit in Sekunden zurück.
    """
    config_path = _neat_config_path()

    config = NeatConfig(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        config_path,
    )

    # Optional: pop_size aus Parametern überschreiben (falls du das möchtest).
    # (NEAT liest pop_size aus der Config; das hier hebt sie ggf. an.)
    if isinstance(pop_size, int) and pop_size > 0:
        try:
            config.pop_size = pop_size
        except Exception:
            pass

    # (optional) Log der Parameter
    with open(_log_path(), encoding="utf-8", mode="a+") as f:
        f.write(str([k1, k2, k3, kp1, kp2]) + ",")

    population = Population(config)
    population.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    population.add_reporter(stats)

    start_time = time.time()
    population.run(run_simulation, 1000)
    end_time = time.time()
    return end_time - start_time


# ------------------------------------------------------------
# Öffentliche API, die die Simulation mit Zeitlimit ausführt
# ------------------------------------------------------------
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
    Führt die Simulation mit Zeitlimit aus und gibt eine „Rundenzeit“-Metrik zurück
    (hier: die Laufzeit bis Abbruch).
    Das Verhalten entspricht dem alten Code: erst werden die Parameter in interface.py geschrieben.
    """
    # Beibehaltung des alten Verhaltens: in Datei schreiben
    _update_parameters_in_interface(k1, k2, k3, kp1, kp2)

    # NEAT-Run in eigenem Prozess starten
    proc = Process(
        target=_run_neat_simulation,
        args=(k1, k2, k3, kp1, kp2, pop_size),
        daemon=True,
    )
    start_time = time.time()
    proc.start()

    # Warten bis zum Time-Limit
    time.sleep(time_limit)

    # Windows-spezifisches, hartes Beenden (wie zuvor)
    # (Unter Linux/MacOS würdest du z.B. proc.terminate() nutzen.)
    os.system(f"taskkill /F /PID {proc.pid}")

    end_time = time.time()
    lap_time = end_time - start_time

    # Logging wie gehabt
    if lap_time >= 20:
        with open(_log_path(), encoding="utf-8", mode="a+") as f:
            f.write("20\n")

    return lap_time


# ------------------------------------------------------------
# Minimizer-Zielfunktion & öffentlicher Einstiegspunkt
# ------------------------------------------------------------
def _objective_function(params):
    """Zielfunktion für die Optimierung (negierte Laufzeit, weil minimize())."""
    k1, k2, k3, kp1, kp2 = params
    return -simulate_car(k1, k2, k3, kp1, kp2)

def run_optimization(
    initial_point=None,
    bounds=None,
    method: str = "L-BFGS-B",
) -> Dict[str, float | bool | str]:
    """
    Öffentlicher Einstiegspunkt (wird von main.py aufgerufen).
    Gibt ein Ergebnis-Dict zurück, kein sys.exit hier!
    """
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20.0)] * 5

    # Log mit Header neu anlegen
    with open(_log_path(), encoding="utf-8", mode="w") as f:
        f.write("Parameter,round_time\n")

    result = minimize(_objective_function, initial_point, method=method, bounds=bounds)
    optimal_k1, optimal_k2, optimal_k3, optimal_kp1, optimal_kp2 = result.x
    optimal_lap_time = -result.fun

    return {
        "k1": float(optimal_k1),
        "k2": float(optimal_k2),
        "k3": float(optimal_k3),
        "kp1": float(optimal_kp1),
        "kp2": float(optimal_kp2),
        "optimal_lap_time": float(optimal_lap_time),
        "success": bool(result.success),
        "message": str(result.message),
    }

__all__ = ["run_optimization", "simulate_car"]
