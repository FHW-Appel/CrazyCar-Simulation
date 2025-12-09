"""CrazyCar Simulation - Evolutionary AI-driven vehicle simulation.

This package contains:
- car: Vehicle model (kinematics, dynamics, sensors, collision)
- sim: Simulation loop, event handling, map service, rendering
- control: NEAT-based neural network control & optimization
- assets: Resources (images, maps, fonts)
- interop: C-extension build tools (CFFI)

The simulation uses pygame for rendering and NEAT-Python for evolutionary
optimization. Vehicles learn autonomously through trial & error.
"""

# Allow submodules to be loaded from build/_cffi/crazycar
import os
_build_pkg = os.path.join(os.path.dirname(__file__), '..', '..', 'build', '_cffi', 'crazycar')
_build_pkg = os.path.normpath(os.path.abspath(_build_pkg))
if os.path.isdir(_build_pkg) and _build_pkg not in __path__:
    __path__.append(_build_pkg)
