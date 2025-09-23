# import pygame  # Für die Optimierung nicht notwendig
# from scipy.optimize import minimize  # Wird weiter unten benutzt
from scipy.optimize import minimize
import neat
import time
import os
from multiprocessing import Process
from simulation import run_simulation

# Schlüssel der zu optimierenden Parameter
DLL_PARAMETER_KEYS = ["k1", "k2", "k3", "kp1", "kp2"]

# Robustere Methode zur Aktualisierung von Parametern in interface.py
def update_parameters_in_interface(k1, k2, k3, kp1, kp2):
    interface_path = os.path.join(os.path.dirname(__file__), "interface.py")

    with open(interface_path, encoding='utf-8', mode='r') as f:
        lines = f.readlines()

    for key in DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            if line.strip().startswith(key):
                parts = line.split('=')
                indent = line[:len(line) - len(line.lstrip())]
                lines[i] = f"{indent}{parts[0].strip()} = {locals()[key]}\n"
                break

    with open(interface_path, encoding='utf-8', mode='w') as f:
        f.writelines(lines)

# Führt eine NEAT-basierte Simulation durch
def run_neat_simulation(k1, k2, k3, kp1, kp2, pop_size: int = 2):
    config_path = os.path.join(os.path.dirname(__file__), "config_neat.txt")
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )
    # Kleine Population zum Testen (konfigurierbar)
    config.pop_size = pop_size

    # Log für Parameter schreiben
    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    with open(log_path, encoding='utf-8', mode='a+') as f:
        f.write(str([k1, k2, k3, kp1, kp2]) + ',')

    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    start_time = time.time()
    population.run(run_simulation, 1000)
    end_time = time.time()

    return end_time - start_time

# Führt die Simulation mit Zeitlimit aus
def simulate_car(k1, k2, k3, kp1, kp2, time_limit: int = 60, pop_size: int = 2):
    # pygame.init()  # Nicht notwendig in diesem Kontext
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)

    cp = Process(target=run_neat_simulation, args=(k1, k2, k3, kp1, kp2, pop_size), daemon=True)
    start_time = time.time()
    cp.start()
    time.sleep(time_limit)  # Simulation nach X Sekunden abbrechen

    # Windows-spezifisch (dein bisheriger Weg):
    os.system(f'taskkill -f -pid {cp.pid}')

    end_time = time.time()
    lap_time = end_time - start_time

    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    if lap_time >= 20:
        with open(log_path, encoding='utf-8', mode='a+') as f:
            f.write('20\n')

    return lap_time

# Zielfunktion für Optimierung
def objective_function(params):
    k1, k2, k3, kp1, kp2 = params
    return -simulate_car(k1, k2, k3, kp1, kp2)  # Negiert für Minimierung

# --- Öffentlicher Einstiegspunkt für main.py (kein eigener Start!) ---
def run_optimization(
    initial_point = None,
    bounds = None,
    method: str = "L-BFGS-B",
):
    """
    Führt die Optimierung über simulate_car() aus und gibt ein Ergebnis-Dict zurück.
    Keine Top-Level-Starts, kein sys.exit – nur Werte zurückgeben.
    """
    # Defaults wie bisher
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20)] * 5

    # Log-Datei mit Header erstellen/überschreiben
    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    with open(log_path, encoding='utf-8', mode='w') as f:
        f.write('Parameter,round_time\n')

    result = minimize(objective_function, initial_point, method=method, bounds=bounds)
    optimal_k1, optimal_k2, optimal_k3, optimal_kp1, optimal_kp2 = result.x
    optimal_lap_time = -result.fun

    # Optional: hier nicht printen – nur zurückgeben; main.py darf entscheiden
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

# ─────────────────────────────────────────────────────────────────────────────
# [ALT/BEHALTEN, aber DEAKTIVIERT]
# Früherer direkter Start. Absichtlich auskommentiert, damit NUR main.py startet.
# 
#
# if __name__ == "__main__":
#     res = run_optimization()
#     print("Optimierte Parameter:")
#     print("K1:", res["k1"])
#     print("K2:", res["k2"])
#     print("K3:", res["k3"])
#     print("Kp1:", res["kp1"])
#     print("Kp2:", res["kp2"])
#     print("Optimale Rundenzeit:", res["optimal_lap_time"])
# ─────────────────────────────────────────────────────────────────────────────
