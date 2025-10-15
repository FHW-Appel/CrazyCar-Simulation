# src/crazycar/main.py
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path

# Einfacher Debug-Schalter: 0 = aus, 1 = an 
DEBUG_DEFAULT = 0

_THIS = Path(__file__).resolve()
_SRC_DIR = _THIS.parents[1]  # .../src
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
print("[sys.path add]", _SRC_DIR)

from crazycar.interop.build_tools import run_build_native  # nur Build-Tool vorab importieren


# ---------------------------------------------------------------------------
# Globaler Quit-Guard für Pygame
# ---------------------------------------------------------------------------
def _install_pygame_quit_guard() -> None:
    """
    Erzwingt einen sofortigen, sauberen Programm-Exit, sobald IRGENDEINE
    Stelle im Code ein Fenster-QUIT- oder ESC-Event erhält – selbst wenn
    tiefere Schleifen das Event nicht korrekt behandeln.
    """
    try:
        import pygame  # wird evtl. erst in der Sim/Optimizer importiert
    except Exception:
        return  # kein pygame verfügbar -> nichts zu tun

    # Bereits gepatcht?
    if getattr(pygame.event, "_crazycar_quit_guard_installed", False):
        return

    _orig_get = pygame.event.get
    _orig_poll = pygame.event.poll

    def _wrap_events(events):
        """
        Überwacht alle Events:
        - X-Button (pygame.QUIT)
        - ESC-Taste (pygame.KEYDOWN mit K_ESCAPE)
        und beendet das Programm sofort sauber.
        """
        for ev in events:
            try:
                if ev.type == pygame.QUIT or (
                    ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE
                ):
                    print("[Quit-Guard] Exit durch Benutzer (X oder ESC).")
                    try:
                        pygame.quit()
                    finally:
                        # harter, aber sauberer Exit → kein STRG+C nötig
                        raise SystemExit(0)
            except Exception:
                # Falls ev kein .type oder .key besitzt
                pass
        return events

    def _get_wrapper(*args, **kwargs):
        return _wrap_events(_orig_get(*args, **kwargs))

    def _poll_wrapper(*args, **kwargs):
        ev = _orig_poll(*args, **kwargs)
        return _wrap_events([ev])[0] if ev else ev

    pygame.event.get = _get_wrapper
    pygame.event.poll = _poll_wrapper
    pygame.event._crazycar_quit_guard_installed = True

    print("[Quit-Guard] Aktiviert – ESC und X beenden das Programm.")
# ---------------------------------------------------------------------------


def main() -> int:
    """Haupteinstiegspunkt für CrazyCar."""
    # Debug initialisieren (nur über den Schalter oben)
    debug = bool(int(DEBUG_DEFAULT))
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s"
    )
    logging.info("Starting CrazyCar (debug=%s)", debug)
    os.environ["CRAZYCAR_DEBUG"] = "1" if debug else "0"

    # Optional: Headless-Option aktivieren, um Fensterflut beim Testen zu vermeiden
    # os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    # -----------------------------------------------------------------------
    # Native Build vorbereiten
    # -----------------------------------------------------------------------
    try:
        rc, build_out_dir = run_build_native()
        if rc != 0:
            print("[ERROR] Native Build fehlgeschlagen (Exit 1).")
        else:
            if build_out_dir and build_out_dir not in sys.path:
                sys.path.insert(0, build_out_dir)
                print("[sys.path add build]", build_out_dir)
            os.environ["CRAZYCAR_NATIVE_PATH"] = build_out_dir
    except Exception as e:
        print(f"[ERROR] Native Build Exception: {e}")

    # -----------------------------------------------------------------------
    # Optimierer starten (nach erfolgreichem Build)
    # -----------------------------------------------------------------------
    from crazycar.control.optimizer import run_optimization

    # Quit-Guard erst JETZT aktivieren – Pygame ist ab hier relevant
    _install_pygame_quit_guard()

    res = run_optimization()
    print("Optimierte Parameter:")
    print(f"K1: {res['k1']}")
    print(f"K2: {res['k2']}")
    print(f"K3: {res['k3']}")
    print(f"Kp1: {res['kp1']}")
    print(f"Kp2: {res['kp2']}")
    print(f"Optimale Rundenzeit: {res['optimal_lap_time']}")
    return 0


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Sauber abbrechen ohne langen Traceback (STRG+C)
        print("\n[main] Abgebrochen (Ctrl+C).")
        sys.exit(130)
