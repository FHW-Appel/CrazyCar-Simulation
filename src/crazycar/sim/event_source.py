# =============================================================================
# crazycar/sim/event_source.py  —  Ereignis-Pipeline (pygame/Headless)
# -----------------------------------------------------------------------------
# Aufgabe:
# - Liest rohe pygame-Events und liefert "normierte" Events (Strings + Payload),
#   die unabhängig von pygame-Details verarbeitet werden können.
# - Separates Polling für Resize-Events.
# - Hält den letzten Raw-Event-Batch (z. B. für Widgets wie ToggleButton).
#
# Öffentliche API:
# - class EventSource:
#       __init__(headless: bool = False)
#       poll() -> list[Event]:            # aktive/aktuelle Eingaben (Tasten/Maus/UI)
#       poll_resize() -> list[Event]:     # nur VIDEORESIZE
#       last_raw() -> list[pygame.Event]: # Roh-Events des letzten poll()-Durchlaufs
#
# Event-Typen (normiert, Beispiele):
#   "QUIT", "ESC", "TOGGLE_TRACKS", "KEY_CHAR", "BACKSPACE",
#   ggf. weitere, die von modes.ModeManager ausgewertet werden.
#
# Hinweise:
# - Headless: ggf. SDL_VIDEODRIVER=dummy beachten; EventSource ist darauf vorbereitet.
# =============================================================================

from __future__ import annotations
from typing import List
import pygame

from .state import SimEvent

class EventSource:
    """
    Kapselt pygame.event.get() und normalisiert auf SimEvent.
    - Headless: liefert stets [].
    - poll_resize(): nur VIDEORESIZE-Ereignisse (verbraucht sie).
    - poll(): alle übrigen Events (verbraucht sie).
    - last_raw(): zuletzt eingelesene Raw-Events (für UI-Widgets).
    """
    def __init__(self, headless: bool = False) -> None:
        self.headless = headless
        self._last_raw: List[pygame.event.Event] = []

    def poll_resize(self) -> List[SimEvent]:
        if self.headless:
            self._last_raw = []
            return []
        raw = pygame.event.get(pygame.VIDEORESIZE)
        self._last_raw = raw
        out: List[SimEvent] = []
        for e in raw:
            size = getattr(e, "size", None)
            out.append(SimEvent("VIDEORESIZE", {"size": size}))
        return out

    def poll(self) -> List[SimEvent]:
        if self.headless:
            self._last_raw = []
            return []
        raw = pygame.event.get()  # alle verbleibenden Events
        self._last_raw = raw
        out: List[SimEvent] = []
        for e in raw:
            t = e.type
            if t == pygame.QUIT:
                out.append(SimEvent("QUIT"))
            elif t == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    out.append(SimEvent("SPACE"))
                elif e.key == pygame.K_ESCAPE:
                    out.append(SimEvent("ESC"))
                elif e.key == pygame.K_t:
                    out.append(SimEvent("TOGGLE_TRACKS"))
                elif getattr(e, "unicode", "") and e.unicode.isalnum():
                    out.append(SimEvent("KEY_CHAR", {"char": e.unicode}))
                elif e.key == pygame.K_BACKSPACE:
                    out.append(SimEvent("BACKSPACE"))
            elif t == pygame.MOUSEBUTTONDOWN:
                out.append(SimEvent("MOUSE_DOWN", {
                    "pos": getattr(e, "pos", (0, 0)),
                    "button": getattr(e, "button", 1),
                }))
            # weitere Events werden bewusst ignoriert
        return out

    def last_raw(self) -> List[pygame.event.Event]:
        return list(self._last_raw)

__all__ = ["EventSource"]
