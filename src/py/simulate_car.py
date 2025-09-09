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
def run_neat_simulation(k1, k2, k3, kp1, kp2):
    config_path = os.path.join(os.path.dirname(__file__), "config_neat.txt")
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )
    config.pop_size = 2  # Kleine Population zum Testen

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
def simulate_car(k1, k2, k3, kp1, kp2):
    # pygame.init()  # Nicht notwendig in diesem Kontext
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)

    cp = Process(target=run_neat_simulation, args=(k1, k2, k3, kp1, kp2), daemon=True)
    start_time = time.time()
    cp.start()
    time.sleep(60)  # Simulation nach 60 Sekunden abbrechen
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

# Hauptprogramm
if __name__ == "__main__":
    # Log-Datei mit Header erstellen
    log_path = os.path.join(os.path.dirname(__file__), "log.csv")
    with open(log_path, encoding='utf-8', mode='w') as f:
        f.write('Parameter,round_time\n')

    # Startwerte und Grenzen für Parameter
    initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    bounds = [(1.1, 20)] * 5

    # Optimierung starten
    result = minimize(objective_function, initial_point, method='L-BFGS-B', bounds=bounds)
    optimal_k1, optimal_k2, optimal_k3, optimal_kp1, optimal_kp2 = result.x
    optimal_lap_time = -result.fun

    print("Optimierte Parameter:")
    print("K1:", optimal_k1)
    print("K2:", optimal_k2)
    print("K3:", optimal_k3)
    print("Kp1:", optimal_kp1)
    print("Kp2:", optimal_kp2)
    print("Optimale Rundenzeit:", optimal_lap_time)
