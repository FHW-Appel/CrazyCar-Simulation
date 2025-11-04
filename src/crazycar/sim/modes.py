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

from .state import SimRuntime
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
                    # Dialog: NO
                    if ui.button_no_rect.collidepoint(pos):
                        if self._button_py:
                            self.regelung_py = True
                            self._button_py = False
                        if self._button_c:
                            self.regelung_py = False
                            self._button_c = False
                        rt.paused = False
                        self.show_dialog = False
                        continue
                    # Dialog: YES (Moduswechsel + akt. Car terminieren)
                    if ui.button_yes_rect.collidepoint(pos):
                        if self._button_py:
                            self.regelung_py = False
                            self._button_py = False
                        if self._button_c:
                            self.regelung_py = True
                            self._button_c = False
                        if cars:
                            cars[0].alive = False
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
                    self.show_dialog = True
                    rt.paused = True
                    self._button_py = True
                    self._button_c = False
                    continue
                # Dialog öffnen: Ziel c_regelung
                if ui.button_regelung1_rect.collidepoint(pos):
                    self.show_dialog = True
                    rt.paused = True
                    self._button_c = True
                    self._button_py = False
                    continue

        return actions

__all__ = ["ModeManager", "UIRects"]
