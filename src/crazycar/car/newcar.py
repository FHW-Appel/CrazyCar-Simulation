# This Code is Heavily Inspired By The YouTuber: Cheesy AI
# Code Changed, Optimized And Commented By: NeuralNine (Florian Dedov)
# Projektanpassung durch eigene Erweiterung für CARSim

import neat
from src.crazycar.sim.simulation import run_simulation
from neat.six_util import iteritems

# ------------------------------------------------------------------------------
# Veraltete / nicht mehr verwendete Konstanten (werden ggf. im Projektverlauf 
# wiederverwendet oder dienen als Referenz für Skalierungsfaktoren)
# ------------------------------------------------------------------------------

# Constants# WIDTH = 1600 # HEIGHT = 880

# f = 1.6
#
# WIDTH = 1920/2 * f     #
# HEIGHT = 1080/2 * f
# window_size = (WIDTH, HEIGHT)
#
# time_flip = 0.01  # 10ms
#
# CAR_SIZE_X = 23.75 * f
# CAR_SIZE_Y = 10 * f
#
# BORDER_COLOR: tuple[int, int, int, int] = (255, 255, 255, 255)  # Color To Crash on Hit

# current_generation = 0  # Generation counter

# ------------------------------------------------------------------------------
# Hauptausführung
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Lade NEAT-Konfiguration aus Projektstruktur
    config_path = "./src/py/config_neat.txt"
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )

    # Hinweis: Die Populationsgröße wird durch die Konfigurationsdatei bestimmt.
    # Falls man sie hier überschreibt, wird dies möglicherweise ignoriert.
    # Daher ist die folgende Zeile aktuell nicht notwendig.
    # config.pop_size = 2

    # Initialisiere Population mit Reporter für Konsolenausgabe
    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))       # Ausgabe im Terminal
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    # Starte die Simulation über maximal 1000 Generationen
    population.run(run_simulation, 1000)
