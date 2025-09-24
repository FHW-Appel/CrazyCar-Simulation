# src/crazycar/interop/build_tools.py
import sys
import subprocess
from pathlib import Path

def run_build_native() -> int:
    # .../src/crazycar/interop/build_tools.py  -> parents[3] == repo-root
    root = Path(__file__).resolve().parents[3]
    build_script = root / "build_native.py"
    if not build_script.exists():
        print(f"[FATAL] {build_script} nicht gefunden!")
        return 1
    try:
        subprocess.check_call([sys.executable, str(build_script)])
    except subprocess.CalledProcessError as e:
        return e.returncode
    print("[INFO] Build abgeschlossen.")
    return 0
