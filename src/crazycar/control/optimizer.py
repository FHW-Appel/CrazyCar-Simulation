# Optimizer-Modul für CrazyCar
# Vorher src/py/simulate_car.py

from __future__ import annotations

import os
import time
import csv
import logging
from multiprocessing import Process
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

# --- NEAT: explizite Importe für besseren Typ-Check (Pylance) ---
from neat.config import Config as NeatConfig
from neat.genome import DefaultGenome
from neat.reproduction import DefaultReproduction
from neat.species import DefaultSpeciesSet
from neat.stagnation import DefaultStagnation
from neat.population import Population
from neat.reporting import StdOutReporter
from neat.statistics import StatisticsReporter

# alt:
# from src.crazycar.sim.simulation import run_simulation
# neu (beibehalten, da main.py den sys.path fix setzt):
from crazycar.sim.simulation import run_simulation

# alt: Schlüssel der zu optimierenden Parameter
# DLL_PARAMETER_KEYS = ["k1", "k2", "k3", "kp1", "kp2"]
# neu: identisch beibehalten
DLL_PARAMETER_KEYS = ["k1", "k2", "k3", "kp1", "kp2"]


# =============================================================================
# Pfade & Logging
# =============================================================================

_BASE_DIR = Path(__file__).resolve().parent          # .../src/crazycar/control
_ROOT_DIR = _BASE_DIR.parent.parent                  # .../src
_LOG_DIR  = _BASE_DIR                                # Logs in control/ (nah am Modul)

_LOG_TXT  = _LOG_DIR / "optimizer.log"
_LOG_CSV  = _LOG_DIR / "log.csv"
_CFG_PATH = _BASE_DIR / "config_neat.txt"           # <-- Konfig liegt hier

# Logging einrichten (Text-Log)
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_logger = logging.getLogger("crazycar.optimizer")
_logger.setLevel(logging.INFO)
# File-Handler (append)
if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == str(_LOG_TXT)
           for h in _logger.handlers):
    fh = logging.FileHandler(_LOG_TXT, encoding="utf-8", mode="a")
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh.setFormatter(fmt)
    _logger.addHandler(fh)


def _csv_write_header_if_needed(path: Path, header: Iterable[str]) -> None:
    """Schreibt eine CSV-Headerzeile, falls Datei leer oder nicht vorhanden."""
    write_header = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if write_header:
            w.writerow(header)


def _csv_append(path: Path, row: Iterable[Any]) -> None:
    """Hängt eine Zeile an die CSV-Datei an."""
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(row)


# Beim Import sicherstellen, dass CSV eine Kopfzeile hat
_csv_write_header_if_needed(
    _LOG_CSV,
    header=["timestamp", "k1", "k2", "k3", "kp1", "kp2", "event", "value"]
)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def update_parameters_in_interface(k1: float, k2: float, k3: float, kp1: float, kp2: float) -> None:
    """
    Schreibt die Parameter-Werte in interface.py (einfacher Text-Rewrite).
    Lässt alte Zeilenstruktur bestehen.
    """
    # alt:
    # base = os.path.dirname(__file__)
    # interface_path = os.path.abspath(os.path.join(base, "..", "control", "interface.py"))
    # neu:
    interface_path = (_BASE_DIR / "interface.py").resolve()

    _logger.info("Update interface.py parameters: %s", {"k1": k1, "k2": k2, "k3": k3, "kp1": kp1, "kp2": kp2})

    with interface_path.open(encoding="utf-8", mode="r") as f:
        lines = f.readlines()

    # NICHTS löschen—nur Zeilen mit Schlüssel ersetzen
    for key in DLL_PARAMETER_KEYS:
        for i, line in enumerate(lines):
            if line.strip().startswith(key):
                parts = line.split("=")
                indent = line[: len(line) - len(line.lstrip())]
                # Zugriff auf den lokalen Funktions-Namensraum:
                lines[i] = f"{indent}{parts[0].strip()} = {locals()[key]}\n"
                break

    with interface_path.open(encoding="utf-8", mode="w") as f:
        f.writelines(lines)


def _load_neat_config(pop_size: Optional[int] = None) -> NeatConfig:
    """
    Lädt die NEAT-Konfiguration robust aus control/config_neat.txt.
    Überschreibt optional pop_size.
    """
    if not _CFG_PATH.exists():
        raise FileNotFoundError(f"NEAT-Config nicht gefunden: {_CFG_PATH}")

    cfg = NeatConfig(
        DefaultGenome,
        DefaultReproduction,
        DefaultSpeciesSet,
        DefaultStagnation,
        str(_CFG_PATH),
    )
    if pop_size is not None:
        # neat.Config hat zur Laufzeit pop_size; Pylance kennt das Attribut nicht
        try:
            cast(Any, cfg).pop_size = int(pop_size)   # ✅ Pylance-sicher
            # cfg.pop_size = int(pop_size)            # alt
            # cfg.pop_size = int(pop_size)  # type: ignore[attr-defined]  # Alternative
        except Exception:
            _logger.warning("Konnte pop_size nicht überschreiben (pop_size=%s). Nutze Wert aus Config.", pop_size)
    return cfg


# =============================================================================
# NEAT-Simulation
# =============================================================================

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
    _logger.info("run_neat_simulation: start (k1=%s, k2=%s, k3=%s, kp1=%s, kp2=%s, pop_size=%s)",
                 k1, k2, k3, kp1, kp2, pop_size)

    # Pylance-freundliche Konstruktion der NEAT-Konfiguration:
    config = _load_neat_config(pop_size=pop_size)

    # CSV-Log: Start
    _csv_append(_LOG_CSV, [time.strftime("%Y-%m-%d %H:%M:%S"), k1, k2, k3, kp1, kp2, "neat_start", ""])

    population = Population(config)
    population.add_reporter(StdOutReporter(True))
    stats = StatisticsReporter()
    population.add_reporter(stats)

    start_time = time.time()
    population.run(run_simulation, 1000)
    end_time = time.time()

    elapsed = end_time - start_time
    _logger.info("run_neat_simulation: done (elapsed=%.3fs)", elapsed)

    # CSV-Log: Ende
    _csv_append(_LOG_CSV, [time.strftime("%Y-%m-%d %H:%M:%S"), k1, k2, k3, kp1, kp2, "neat_end", f"{elapsed:.3f}"])

    return elapsed


def _terminate_process_hard(pid: int) -> None:
    """
    Fallback-Killer für Windows, falls terminate/join nicht greift.
    """
    try:
        # Windows
        os.system(f"taskkill /T /F /PID {pid}")
    except Exception as e:
        _logger.warning("taskkill failed (pid=%s): %s", pid, e)


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
    _logger.info("simulate_car: start (limit=%ss)", time_limit)
    update_parameters_in_interface(k1, k2, k3, kp1, kp2)

    # CSV-Log: Parameter
    _csv_append(_LOG_CSV, [time.strftime("%Y-%m-%d %H:%M:%S"), k1, k2, k3, kp1, kp2, "params_set", ""])

    cp = Process(
        target=run_neat_simulation,
        args=(k1, k2, k3, kp1, kp2, pop_size),
        daemon=True,
    )
    start_time = time.time()
    cp.start()
    _logger.info("spawned process pid=%s", cp.pid)

    # Nach X Sekunden abbrechen
    time.sleep(time_limit)

    # Versuch sanft zu terminieren
    if cp.is_alive():
        _logger.info("time limit reached → terminate()")
        cp.terminate()
        cp.join(timeout=3)

    # Notfalls hart beenden (pid kann None sein → prüfen)
    if cp.is_alive():
        _logger.info("process still alive → taskkill fallback")
        pid = cp.pid
        if pid is not None:
            try:
                _terminate_process_hard(pid)
            finally:
                cp.join(timeout=1)
        else:
            _logger.warning("taskkill fallback: pid is None (Prozess evtl. bereits beendet)")

    end_time = time.time()
    lap_time = end_time - start_time

    # CSV-Log: Ergebnis
    event_val = ">=20" if lap_time >= 20 else f"{lap_time:.3f}"
    _csv_append(_LOG_CSV, [time.strftime("%Y-%m-%d %H:%M:%S"), k1, k2, k3, kp1, kp2, "lap_time", event_val])

    _logger.info("simulate_car: done (lap_time=%.3fs)", lap_time)
    return lap_time


def objective_function(params: Iterable[float]) -> float:
    """
    Zielfunktion für die Optimierung (negierte Laufzeit, weil minimize()).
    """
    k1, k2, k3, kp1, kp2 = params
    val = -simulate_car(k1, k2, k3, kp1, kp2)
    _logger.info("objective_function: params=%s → value=%.3f", params, val)
    return val


# --- Öffentlicher Einstiegspunkt für main.py (kein eigener Start!) ---
def run_optimization(
    initial_point: Optional[List[float]] = None,
    bounds: Optional[List[Tuple[float, float]]] = None,
    method: str = "L-BFGS-B",
) -> Dict[str, Any]:
    """
    Führt die Optimierung über simulate_car() aus und gibt ein Ergebnis-Dict zurück.
    Keine Top-Level-Starts, kein sys.exit – nur Werte zurückgeben.
    """
    # Defaults wie bisher
    if initial_point is None:
        initial_point = [1.1, 1.1, 1.1, 1.0, 1.0]
    if bounds is None:
        bounds = [(1.1, 20.0)] * 5   # ✅ float statt int

    # CSV-Header sicherstellen und Start loggen
    _csv_write_header_if_needed(
        _LOG_CSV,
        header=["timestamp", "k1", "k2", "k3", "kp1", "kp2", "event", "value"]
    )
    _csv_append(_LOG_CSV, [time.strftime("%Y-%m-%d %H:%M:%S"), *initial_point, "opt_start", method])

    _logger.info("run_optimization: start method=%s, x0=%s, bounds=%s", method, initial_point, bounds)

    from scipy.optimize import minimize  # Import hier lassen (war vorher top-level)
    result = minimize(objective_function, initial_point, method=method, bounds=bounds)

    optimal_k1, optimal_k2, optimal_k3, optimal_kp1, optimal_kp2 = result.x
    optimal_lap_time = -result.fun

    _logger.info("run_optimization: done success=%s, msg=%s", result.success, result.message)
    _csv_append(_LOG_CSV, [
        time.strftime("%Y-%m-%d %H:%M:%S"),
        float(optimal_k1), float(optimal_k2), float(optimal_kp1), float(optimal_kp2), float(optimal_k3),
        "opt_end",
        f"{optimal_lap_time:.3f}"
    ])

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

# Wichtig: KEIN if __name__ == "__main__" hier.
# Der Aufruf kommt aus main.py, das bereits einen __main__-Guard besitzt.
