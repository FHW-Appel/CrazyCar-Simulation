# src/crazycar/interop/build_tools.py
from __future__ import annotations
import os
import sys
from pathlib import Path
from cffi import FFI
import sysconfig

ROOT = Path(__file__).resolve().parents[3]     # .../CrazyCar-Simulation
SRC  = ROOT / "src"
PKG  = "crazycar"

C_DIR = SRC / "c"                              
OUT_BASE = ROOT / "build" / "_cffi"            
OUT_PKG  = OUT_BASE / PKG

def run_build_native():
    """
    Baut das native Modul als .pyd nach build/_cffi/crazycar/.
    Gibt (rc, sys_path_dir) zurück – sys_path_dir solltest du vor den Import schieben.
    """
    OUT_PKG.mkdir(parents=True, exist_ok=True)

    # --- CFFI Setup ---
    ffi = FFI()

    # 1) cdef: nur das, was du aus Python nutzt
    ffi.cdef(r"""
        void getfahr(int value);
        void getservo(int value);
        void getabstandvorne(int value);
        void getabstandrechts(int value, int cosAlpha);
        void getabstandlinks(int value, int cosAlpha);
        void regelungtechnik(void);

        int  getfwert(void);
        int  getswert(void);
        int  get_abstandvorne(void);
        int  get_abstandrechts(void);
        int  get_abstandlinks(void);
    """)

    # 2) set_source: Quellfiles und Include-Verzeichnisse angeben
    #    Der Modulname MUSS "crazycar.carsim_native" sein, damit "from crazycar import carsim_native" klappt.
    ext_suffix = sysconfig.get_config_var("EXT_SUFFIX")  # z.B. .cp313-win_amd64.pyd
    target_file = OUT_PKG / f"carsim_native{ext_suffix}"

    ffi.set_source(
        f"{PKG}.carsim_native",              # Modulname
        r"""
        #include "IF.h"
        """,
        sources=[
            str(C_DIR / "IF.c"),
            str(C_DIR / "myfunktion.c"),
        ],
        include_dirs=[str(C_DIR)],
        define_macros=[],
        extra_compile_args=[],
        extra_link_args=[],
    )

    # 3) Compile: Out-of-tree ZIEL
    rc = 0
    try:
        ffi.compile(
            verbose=True,
            tmpdir=str(OUT_BASE),            # temporäre Buildartefakte
            target=str(target_file),         # finale .pyd an genau diesen Ort
        )
    except Exception as e:
        print("[build_native] Fehler:", e)
        rc = 1

    # Wir geben den Ordner zurück, den du in sys.path aufnehmen sollst
    return rc, str(OUT_BASE)
