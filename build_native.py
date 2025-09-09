# build_native.py
from cffi import FFI
from pathlib import Path
from importlib.machinery import EXTENSION_SUFFIXES  # <- liefert z.B. ".cp313-win_amd64.pyd"

ROOT = Path(__file__).resolve().parent
SRC_C = ROOT / "src" / "c"

ffi = FFI()
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

ffi.set_source(
    "carsim_native",
    r"""
    #include "if.h"
    #include "mf.h"
    """,
    sources=[str(SRC_C / "IF.c"), str(SRC_C / "myfunktion.c")],
    include_dirs=[str(SRC_C)],
)

if __name__ == "__main__":
    # korrektes Extension-Suffix (z.B. ".cp313-win_amd64.pyd")
    suffix = EXTENSION_SUFFIXES[0]
    target_path = ROOT / "src" / "py" / f"carsim_native{suffix}"

    (ROOT / "build" / "_cffi").mkdir(parents=True, exist_ok=True)

    ffi.compile(
        verbose=True,
        tmpdir=str(ROOT / "build" / "_cffi"),
        target=str(target_path),
    )
    print("Built:", target_path)
