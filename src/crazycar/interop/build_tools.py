"""Build Tools - Native C extension compilation via CFFI.

Responsibilities:
- Configure and build carsim_native extension
- Define C function signatures for CFFI
- Manage build output directories
- Ensure build/_cffi is on sys.path for imports

Public API:
- ensure_build_on_path() -> str:
      Add build/_cffi to sys.path
      Returns the build directory path
      
- run_build_native(clean: bool = True) -> tuple[int, str]:
      Compile native C extension
      Returns (exit_code, sys_path_dir)

Paths:
- ROOT: CrazyCar-Simulation/
- SRC_C: ROOT/src/c/
- OUT_BASE: ROOT/build/_cffi/
- OUT_PKG: ROOT/build/_cffi/crazycar/

C Sources:
- sim_globals.c: Global variables
- cc-lib.c: C API functions
- myFunktions.c: Control logic (fahren1, regelungtechnik)

Usage:
    # Build extension
    rc, build_dir = run_build_native()
    
    # Ensure importable
    ensure_build_on_path()
    import crazycar.carsim_native

Notes:
- Uses CFFI for Python-C interop
- Builds to build/_cffi/crazycar/carsim_native.*.pyd (Windows)
- Clean build removes old artifacts to prevent stale loads
- Symbol probe validates all expected functions present
"""
# src/crazycar/interop/build_tools.py
from __future__ import annotations
import sys
import sysconfig
import logging
from pathlib import Path
from cffi import FFI

log = logging.getLogger(__name__)

# Paths
ROOT     = Path(__file__).resolve().parents[3]      # .../CrazyCar-Simulation
SRC_C    = ROOT / "src" / "c"
OUT_BASE = ROOT / "build" / "_cffi"
OUT_PKG  = OUT_BASE / "crazycar"

def ensure_build_on_path() -> str:
    """Ensure build/_cffi is importable (for crazycar.carsim_native)."""
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    p = str(OUT_BASE)
    if p not in sys.path:
        sys.path.insert(0, p)
    return p

def _make_ffi() -> FFI:
    """Create FFI instance with C function declarations.
    
    Defines all exported C functions from the native extension:
    - Legacy control: fahr, servo, getfwert, getswert
    - New control API: getfahr, getFahr, getservo, getServo
    - Distance sensors: getabstandvorne, getabstandrechts, getabstandlinks
    - Control logic: regelungtechnik
    - Getters: get_abstandvorne, get_abstandrechts, get_abstandlinks
    
    Returns:
        FFI instance configured with C declarations
        
    Notes:
        Only uses basic C types (no stdint.h) for CFFI compatibility
    """
    ffi = FFI()
    # IMPORTANT: Only use basic types in cdef (no stdint.h).
    ffi.cdef(r"""
        /* ---- Legacy + new Control API ---- */
        void fahr(int f);
        int  getfwert(void);
        void servo(int s);
        int  getswert(void);

        void         getfahr(signed char leistung);
        signed char  getFahr(void);
        void         getservo(signed char winkel);
        signed char  getServo(void);

        void getabstandvorne(unsigned short analogwert);
        void getabstandrechts(unsigned short analogwert, unsigned char cosAlpha);
        void getabstandlinks(unsigned short analogwert, unsigned char cosAlpha);

        void regelungtechnik(void);

        unsigned short get_abstandvorne(void);
        unsigned short get_abstandrechts(void);
        unsigned short get_abstandlinks(void);
    """)
    return ffi

def run_build_native(clean: bool = True) -> tuple[int, str]:
    """
    Build the native module to build/_cffi/crazycar/.
    Returns: (rc, sys_path_dir)
    """
    OUT_PKG.mkdir(parents=True, exist_ok=True)

    ffi = _make_ffi()

    # Target filename
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not ext_suffix:
        from importlib.machinery import EXTENSION_SUFFIXES
        ext_suffix = EXTENSION_SUFFIXES[0]
    target = OUT_PKG / f"carsim_native{ext_suffix}"

    # Sources: Globals, C-API, Control logic
    sources = [str(SRC_C / n) for n in ("sim_globals.c", "cc-lib.c", "myFunktions.c")]

    ffi.set_source(
        "crazycar.carsim_native",
        '#include "cc-lib.h"\n',
        sources=sources,
        include_dirs=[str(SRC_C)],
        define_macros=[("CC_EXPORTS", None)],   # Ok on Windows for __declspec(dllexport)
        extra_compile_args=[],
        extra_link_args=[],
    )

    # Optionally remove old artifacts (prevents stale loads)
    if clean:
        for p in OUT_PKG.glob("carsim_native*.*"):
            try:
                p.unlink()
            except Exception:
                pass

    rc = 0
    try:
        ffi.compile(verbose=True, tmpdir=str(OUT_BASE), target=str(target))
    except Exception as e:
        log.error("[build_tools] compile error: %s", e)
        rc = 1

    return rc, str(OUT_BASE)

def _print_symbol_probe() -> None:
    """Load module and check if expected symbols are present."""
    try:
        ensure_build_on_path()
        import importlib
        mod = importlib.import_module("crazycar.carsim_native")
        lib = mod.lib
        present = {name: hasattr(lib, name) for name in (
            "fahr","getfwert","servo","getswert",
            "getfahr","getFahr","getservo","getServo",
            "getabstandvorne","getabstandrechts","getabstandlinks",
            "regelungtechnik",
            "get_abstandvorne","get_abstandrechts","get_abstandlinks",
        )}
        log.info("[build_tools] loaded: %s", getattr(mod, "__file__", "?"))
        log.debug("[build_tools] present symbols: %s", present)
    except Exception as e:
        log.error("[build_tools] import/probe error: %s", e)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rc, sp = run_build_native()
    ensure_build_on_path()
    log.info("rc = %s | sys.path += %s", rc, sp)
    _print_symbol_probe()
