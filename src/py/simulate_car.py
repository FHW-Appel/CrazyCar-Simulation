# src/py/simulate_car.py

from scipy.optimize import minimize
import time
import os
from multiprocessing import Process

# NEAT: explizite Importe für besseren Typ-Check (Pylance)
from neat.config import Config as NeatConfig
from neat.genome import DefaultGenome
from neat.reproduction import DefaultReproduction
from neat.species import DefaultSpeciesSet
from neat.stagnation import DefaultStagnation
from neat.population import Population
from neat.reporting import StdOutReporter
from neat.statistics import StatisticsReporter

from simulation import run_simulation

# Schlüssel der zu optimierenden Parameter
DLL_PARAMETER_KEYS = ["k1", "k2", "k3", "kp1", "kp2"]


def update_parameters_in_interface(k1: float, k2: float, k3: float, kp1: float, kp2: float) -> None:
    """Schreibt die Parameter-Werte in interface.py (einfacher Text-Rewrite)."""
    import os

    interface_path = os.path.join(os.path.dirname(__file__), "interface.py")

    with open(interface_path, encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    for key in DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            if line.strip().startswith(key):
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
                # Zugriff auf den lokalen Funktions-Namensraum:
                lines[i] = f"{indent}{parts[0].strip()} = {locals()[key]}\n"
                break

    with open(interface_path, encoding="utf-8", mode="w") as f:
        f.writelines(lines)


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
    """
    import os

    config_path = os.path.join(os.path.dirname(__file__), "config_neat.txt")

    # Pylance-freundliche Konstruktion der NEAT-Konfiguration:
    config = NeatConfig(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        config_path,
    )
     

    # Log für Parameter schreiben
    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    with open(log_path, encoding="utf-8", mode="a+") as f:
        f.write(str([k1, k2, k3, kp1, kp2]) + ",")

    population = Population(config)
    population.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    population.add_reporter(stats)

    start_time = time.time()
    population.run(run_simulation, 1000)
    end_time = time.time()

    return end_time - start_time


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
    Führt eine Simulation mit Zeitlimit aus und gibt die "Rundenzeit" (hier: Laufzeit bis Abbruch) zurück.
    """
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)

    cp = Process(
        target=run_neat_simulation,
        args=(k1, k2, k3, kp1, kp2, pop_size),
        daemon=True,
    )
    start_time = time.time()
    cp.start()

    # Nach X Sekunden abbrechen
    time.sleep(time_limit)

    # Windows-spezifisch (wie vorher): hart beenden
    os.system(f"taskkill -f -pid {cp.pid}")

    end_time = time.time()
    lap_time = end_time - start_time

    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    if lap_time >= 20:
        with open(log_path, encoding="utf-8", mode="a+") as f:
            f.write("20\n")

    return lap_time


def objective_function(params):
    """
    Zielfunktion für die Optimierung (negierte Laufzeit, weil minimize()).
    """
    k1, k2, k3, kp1, kp2 = params
    return -simulate_car(k1, k2, k3, kp1, kp2)


# --- Öffentlicher Einstiegspunkt für main.py (kein eigener Start!) ---
def run_optimization(
    initial_point=None,
    bounds=None,
    method: str = "L-BFGS-B",
):
    """
    Führt die Optimierung über simulate_car() aus und gibt ein Ergebnis-Dict zurück.
    Keine Top-Level-Starts, kein sys.exit – nur Werte zurückgeben.
    """
    import os

    # Defaults wie bisher
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20)] * 5

    # Log-Datei mit Header erstellen/überschreiben
    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    with open(log_path, encoding="utf-8", mode="w") as f:
        f.write("Parameter,round_time\n")

    result = minimize(objective_function, initial_point, method=method, bounds=bounds)
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
