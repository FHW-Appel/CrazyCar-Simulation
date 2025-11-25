from cffi import FFI
from pathlib import Path
from importlib.machinery import EXTENSION_SUFFIXES
import sys
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent
SRC_C = ROOT / "src" / "c"

OUT_BASE = ROOT / "build" / "_cffi"
OUT_PKG  = OUT_BASE / "crazycar"
OUT_PKG.mkdir(parents=True, exist_ok=True)

ffi = FFI()
ffi.cdef(r"""  /* … deine API bleibt identisch … */  """)

sources = [
    str(SRC_C / "sim_globals.c"),
    str(SRC_C / "cc-lib.c"),
    str(SRC_C / "myFunktions.c"),
]

# Wenn du zusätzlich eine echte DLL bauen willst, behandle das in einem separaten Build.

ffi.set_source(
    "crazycar.carsim_native",
    r"""
    #include <stdint.h>
    #include "cc-lib.h"
    """,
    sources=sources,
    include_dirs=[str(SRC_C)],
    define_macros=[("CC_EXPORTS", None)],  # ok, schadet nicht
)

if __name__ == "__main__":
    suffix = EXTENSION_SUFFIXES[0]
    target_path = OUT_PKG / f"carsim_native{suffix}"
    ffi.compile(verbose=True, tmpdir=str(OUT_BASE), target=str(target_path))
    log.info("Built: %s", target_path)
