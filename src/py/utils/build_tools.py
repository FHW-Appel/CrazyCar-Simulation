# src/py/utils/build_tools.py
import sys, subprocess
from pathlib import Path

def run_build_native() -> int:
    root = Path(__file__).resolve().parents[3]  # .../repo-root (utils liegt tiefer)
    build_script = root / "build_native.py"
    if not build_script.exists():
        print(f"[FATAL] {build_script} nicht gefunden!")
        return 1
    subprocess.check_call([sys.executable, str(build_script)])
    print("[INFO] Build abgeschlossen.")
    return 0
