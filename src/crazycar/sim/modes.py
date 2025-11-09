# =============================================================================
# crazycar/sim/modes.py  —  Modus-/Pausenlogik & Dialogsteuerung
# -----------------------------------------------------------------------------
# Aufgabe:
# - Zuständig für:
#     * Pause an/aus (SPACE)
#     * Modus-Umschaltung Python-Regelung ↔ C-Regelung inkl. Bestätigungsdialog
#     * Snapshot/Recovery-Trigger über UI-Buttons
# - Hält UI-Dialog-Status (show_dialog) und aktuelle Regelung (regelung_py).
#
# Öffentliche API:
# - @dataclass UIRects:
#       aufnahmen_button, recover_button
#       button_yes_rect, button_no_rect
#       button_regelung1_rect, button_regelung2_rect
# - class ModeManager:
#       regelung_py: bool
#       show_dialog: bool
#       __init__(start_python: bool = True)
#       apply(events: list[Event], rt: SimRuntime, ui: UIRects, cars: list[Car]) -> dict:
#           # gibt Aktionen zurück, z. B. {"take_snapshot": True} oder {"recover_snapshot": True}
#
# Hinweise:
# - ESC/QUIT werden NICHT hier beendet; das macht die aufrufende Ebene (loop/simulation).
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pygame
import logging

from .state import SimRuntime
import os
from ..car.model import f  # nur falls wir später Skalierungen brauchen

@dataclass
class UIRects:
    aufnahmen_button: pygame.Rect
    recover_button: pygame.Rect
    button_yes_rect: pygame.Rect
    button_no_rect: pygame.Rect
    button_regelung1_rect: pygame.Rect  # "c_regelung"
    button_regelung2_rect: pygame.Rect  # "python_regelung"

class ModeManager:
    """
    Verwaltet Pausen-/Dialoglogik & Regelungsmodus (PY/C).
    - Entkoppelt 'was passieren soll' von 'wie gezeichnet wird'.
    - Liefert Actions an den Aufrufer zurück (take_snapshot, recover_snapshot).
    """
    def __init__(self, start_python: bool = True) -> None:
        self.regelung_py: bool = start_python
        self.show_dialog: bool = False
        self._button_py: bool = False
        self._button_c: bool = False

    def apply(self, events: List, rt: SimRuntime, ui: UIRects, cars) -> Dict[str, bool]:
        """
        Verarbeitet Events sowohl im aktiven als auch im Pausenmodus.
        Gibt Aktionen zurück, die der Aufrufer ausführt:
          - take_snapshot: Momentaufnahme auslösen
          - recover_snapshot: Wiederherstellung auslösen
        """
        actions = {"take_snapshot": False, "recover_snapshot": False}

        for ev in events:
            et = getattr(ev, "type", None)

            # lightweight logger for mode actions
            log = logging.getLogger("crazycar.sim.modes")

            # -------------------------
            # Tasten, die immer gelten
            # -------------------------
            if et == "SPACE":
                # Toggle Pause
                rt.paused = not rt.paused
                continue

            # -------------------------
            # Wenn pausiert: Dialogsteuerung
            # -------------------------
            if rt.paused:
                if et == "MOUSE_DOWN":
                    pos = ev.payload["pos"]
                    # Pause per Aufnahme-Button verlassen (kein Snapshot in Pause)
                    if ui.aufnahmen_button.collidepoint(pos):
                        rt.paused = False
                        continue
                    # Dialog: NO -> Abbrechen (keine Modusänderung)
                    if ui.button_no_rect.collidepoint(pos):
                        log.debug("ModeManager: Dialog NO clicked at %s — canceling mode change", pos)
                        # clear temporary selection flags, keep current mode
                        self._button_py = False
                        self._button_c = False
                        rt.paused = False
                        self.show_dialog = False
                        continue
                    # Dialog: YES (Moduswechsel → Modus setzen + akt. Car terminieren)
                    if ui.button_yes_rect.collidepoint(pos):
                        log.debug("ModeManager: Dialog YES clicked at %s — applying pending selection (py=%s, c=%s)", pos, self._button_py, self._button_c)
                        # If the user requested python_regelung, enable it
                        if self._button_py:
                            log.info("ModeManager: switching to PYTHON regulator (restart requested)")
                            # Persist choice so a restarted simulation honors it
                            try:
                                path = os.path.join(os.getcwd(), ".crazycar_start_mode")
                                with open(path, "w", encoding="utf-8") as _f:
                                    _f.write("1")
                                log.debug("ModeManager: persisted start-mode file %s", path)
                            except Exception as _e:
                                log.warning("ModeManager: could not persist start-mode file: %r", _e)
                            # also set env var for in-process callers (best-effort)
                            os.environ["CRAZYCAR_START_PYTHON"] = "1"
                            self.regelung_py = True
                            self._button_py = False
                        # If the user requested c_regelung, disable python mode
                        if self._button_c:
                            log.info("ModeManager: switching to C regulator (restart requested)")
                            try:
                                path = os.path.join(os.getcwd(), ".crazycar_start_mode")
                                with open(path, "w", encoding="utf-8") as _f:
                                    _f.write("0")
                                log.debug("ModeManager: persisted start-mode file %s", path)
                            except Exception as _e:
                                log.warning("ModeManager: could not persist start-mode file: %r", _e)
                            os.environ["CRAZYCAR_START_PYTHON"] = "0"
                            self.regelung_py = False
                            self._button_c = False
                        # terminate current car so optimizer/spawn logic can restart
                        if cars:
                            try:
                                cars[0].alive = False
                            except Exception:
                                # best-effort only
                                pass
                        rt.paused = False
                        self.show_dialog = False
                        continue
                # andere Events in Pause ignorieren
                continue

            # -------------------------
            # Aktiver Modus (nicht pausiert)
            # -------------------------
            if et == "MOUSE_DOWN":
                pos = ev.payload["pos"]
                # Aufnahme im aktiven Modus: Snapshot auslösen & in Pause gehen
                if ui.aufnahmen_button.collidepoint(pos):
                    actions["take_snapshot"] = True
                    rt.paused = True
                    continue
                # Snapshot wiederherstellen
                if ui.recover_button.collidepoint(pos):
                    actions["recover_snapshot"] = True
                    continue
                # Dialog öffnen: Ziel python_regelung
                if ui.button_regelung2_rect.collidepoint(pos):
                    log.debug("ModeManager: python button clicked at %s — opening dialog", pos)
                    self.show_dialog = True
                    rt.paused = True
                    self._button_py = True
                    self._button_c = False
                    continue
                # Dialog öffnen: Ziel c_regelung
                if ui.button_regelung1_rect.collidepoint(pos):
                    log.debug("ModeManager: c button clicked at %s — opening dialog", pos)
                    self.show_dialog = True
                    rt.paused = True
                    self._button_c = True
                    self._button_py = False
                    continue

        return actions

__all__ = ["ModeManager", "UIRects"]
