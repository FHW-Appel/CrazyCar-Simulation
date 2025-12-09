"""Interop Package - C-Extension Build Tools.

Contains utilities for building the native C-extension (CFFI):

Modules:
- build_tools: CFFI build process, compiler configuration

The C-extension (carsim_native.pyd/.so) contains optimized
calculations for performance-critical operations.

Build Process:
    from crazycar.interop.build_tools import run_build_native
    rc, build_dir = run_build_native(clean=True)

Output: build/_cffi/crazycar/carsim_native.cp3XX-*.pyd
"""
