# src/crazycar/interop/build_tools.py
from __future__ import annotations
import sys
import sysconfig
from pathlib import Path
from cffi import FFI

# Pfade
ROOT     = Path(__file__).resolve().parents[3]      # .../CrazyCar-Simulation
SRC_C    = ROOT / "src" / "c"
OUT_BASE = ROOT / "build" / "_cffi"
OUT_PKG  = OUT_BASE / "crazycar"

def ensure_build_on_path() -> str:
    """Sorgt dafür, dass build/_cffi importierbar ist (für crazycar.carsim_native)."""
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    p = str(OUT_BASE)
    if p not in sys.path:
        sys.path.insert(0, p)
    return p

def _make_ffi() -> FFI:
    ffi = FFI()
    # WICHTIG: In cdef nur Grundtypen verwenden (kein stdint.h).
    ffi.cdef(r"""
        /* ---- Legacy + neue Control-API ---- */
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
    Baut das native Modul nach build/_cffi/crazycar/.
    Rückgabe: (rc, sys_path_dir)
    """
    OUT_PKG.mkdir(parents=True, exist_ok=True)

    ffi = _make_ffi()

    # Ziel-Dateiname
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not ext_suffix:
        from importlib.machinery import EXTENSION_SUFFIXES
        ext_suffix = EXTENSION_SUFFIXES[0]
    target = OUT_PKG / f"carsim_native{ext_suffix}"

    # Quellen: Globals, C-API, Fahrlogik
    sources = [str(SRC_C / n) for n in ("sim_globals.c", "cc-lib.c", "myFunktions.c")]

    ffi.set_source(
        "crazycar.carsim_native",
        '#include "cc-lib.h"\n',
        sources=sources,
        include_dirs=[str(SRC_C)],
        define_macros=[("CC_EXPORTS", None)],   # ok unter Windows für __declspec(dllexport)
        extra_compile_args=[],
        extra_link_args=[],
    )

    # alte Artefakte optional entfernen (verhindert Stale-Loads)
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
        print("[build_tools] compile error:", e)
        rc = 1

    return rc, str(OUT_BASE)

def _print_symbol_probe() -> None:
    """Lädt das Modul und prüft, ob die erwarteten Symbole vorhanden sind."""
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
        print("[build_tools] loaded:", getattr(mod, "__file__", "?"))
        print("[build_tools] present symbols:", present)
    except Exception as e:
        print("[build_tools] import/probe error:", e)

if __name__ == "__main__":
    rc, sp = run_build_native()
    ensure_build_on_path()
    print("rc =", rc, "| sys.path +=", sp)
    _print_symbol_probe()
