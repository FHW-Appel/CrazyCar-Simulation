# src/crazycar/interop/build_tools.py
from __future__ import annotations
import sys
from pathlib import Path
from cffi import FFI
import sysconfig

ROOT = Path(__file__).resolve().parents[3]   # .../CrazyCar-Simulation
SRC  = ROOT / "src"
PKG  = "crazycar"

C_DIR    = SRC / "c"                         # enthält cc-lib.h, myFunktions.h, *.c
OUT_BASE = ROOT / "build" / "_cffi"
OUT_PKG  = OUT_BASE / PKG

def run_build_native():
    """
    Baut das native Modul als .pyd/.so nach build/_cffi/crazycar/.
    Gibt (rc, sys_path_dir) zurück – sys_path_dir vor Import in sys.path legen.
    """
    OUT_PKG.mkdir(parents=True, exist_ok=True)

    ffi = FFI()

    # Öffentliche C-API (entspricht cc-lib.h)
    ffi.cdef(r"""
        void     fahr(int f);
        int      getfwert(void);
        void     servo(int s);
        int      getswert(void);
        void     getfahr(int8_t leistung);
        void     getservo(int8_t winkel);
        void     getabstandvorne(uint16_t analogwert);
        void     getabstandrechts(uint16_t analogwert, uint8_t cosAlpha);
        void     getabstandlinks(uint16_t analogwert, uint8_t cosAlpha);
        void     regelungtechnik(void);
        int8_t   getFahr(void);
        int8_t   getServo(void);
        uint16_t get_abstandvorne(void);
        uint16_t get_abstandrechts(void);
        uint16_t get_abstandlinks(void);
    """)

    # Ziel-Datei (unter build/_cffi/crazycar/)
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")  # z.B. .cp313-win_amd64.pyd
    target_file = OUT_PKG / f"carsim_native{ext_suffix}"

    # Quellen: genau die 4 Sim-Files (dllmain.c nur auf Windows)
    sources = [
        str(C_DIR / "sim_globals.c"),
        str(C_DIR / "cc-lib.c"),
        str(C_DIR / "myFunktions.c"),
    ]
    if sys.platform.startswith("win"):
        sources.append(str(C_DIR / "dllmain.c"))

    ffi.set_source(
        f"{PKG}.carsim_native",
        r"""
        #include <stdint.h>
        #include "cc-lib.h"
        """,
        sources=sources,
        include_dirs=[str(C_DIR)],
        define_macros=[("CC_EXPORTS", None)],  # harmless auch wenn dein Header direkt __declspec benutzt
        extra_compile_args=[],
        extra_link_args=[],
    )

    rc = 0
    try:
        ffi.compile(
            verbose=True,
            tmpdir=str(OUT_BASE),
            target=str(target_file),
        )
    except Exception as e:
        print("[build_native] Fehler:", e)
        rc = 1

    # Diesen Ordner in sys.path aufnehmen, damit 'crazycar.carsim_native' importierbar ist
    return rc, str(OUT_BASE)
