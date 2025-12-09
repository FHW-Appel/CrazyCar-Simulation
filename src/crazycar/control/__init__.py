"""Control Package - Neural Network Control & NEAT Optimization.

Implements evolutionary AI control using NEAT-Python:

Modules:
- interface: Connection Car ↔ Neural Network (Sensor → NN → Actuation)
- optimizer_api: High-level NEAT optimization (generations, fitness)
- optimizer_adapter: Parallelization & multiprocessing
- optimizer_workers: Worker processes for distributed training

Workflow:
1. NEAT generates genomes (network topologies)
2. interface.run_agent() executes simulation with genome
3. Fitness = distance + time bonus - collision penalty
4. NEAT selects best genomes → next generation

Configuration:
- config_neat.txt: NEAT parameters (population, mutation, etc.)
"""
