import os
# Ensure package import
import sys
_THIS = os.path.dirname(__file__)
SRC = os.path.abspath(os.path.join(_THIS, '..', 'src'))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# Set debug envs
os.environ['CRAZYCAR_DEBUG'] = '1'
os.environ['CRAZYCAR_START_PYTHON'] = '1'

# Run the direct mode for 5 seconds
from crazycar.sim import simulation
print('Starting 5s debug run...')
simulation.run_direct(duration_s=5.0)
print('Finished 5s debug run')
