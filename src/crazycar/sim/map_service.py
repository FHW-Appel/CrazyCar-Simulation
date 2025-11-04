# =============================================================================
# crazycar/sim/map_service.py  —  Karte/Track laden, skalieren, blitten
# -----------------------------------------------------------------------------
# Aufgabe:
# - Lädt die Track-Grafik (z. B. "Racemap.png") aus dem Assets-Verzeichnis.
# - Skaliert auf aktuelle Fenstergröße; stellt blit(screen) bereit.
# - Reagiert auf Window-Resize via resize(new_size).
#
# Öffentliche API:
# - class MapService:
#       __init__(window_size: tuple[int,int], asset_name: str = "Racemap.png")
#       resize(window_size: tuple[int,int]) -> None
#       blit(screen: pygame.Surface) -> None
#
# Hinweise:
# - Erweiterbar: Kollision-/Tilemap-Abfragen, mehrere Layer, dynamische Tracks.
# =============================================================================

from __future__ import annotations
import os
import logging
import pygame
from typing import Tuple

log = logging.getLogger("crazycar.sim.map")

class MapService:
    """
    Lädt die Racemap einmal (raw) und hält eine zur Fenstergröße skalierte Surface.
    - resize(new_size): skaliert aus dem Raw neu
    - blit(screen): zeichnet den aktuellen Map-Frame als Hintergrund
    """
    def __init__(self, window_size: Tuple[int, int], asset_name: str = "Racemap.png") -> None:
        assets_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", asset_name))
        log.debug("Lade Map: %s", assets_path)
        self._raw = pygame.image.load(assets_path).convert()
        self._surface = pygame.transform.scale(self._raw, window_size)

    def resize(self, window_size: Tuple[int, int]) -> None:
        self._surface = pygame.transform.scale(self._raw, window_size)

    def blit(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    @property
    def surface(self) -> pygame.Surface:
        """Aktuell skalierte Map-Surface (falls jemand direkten Zugriff braucht)."""
        return self._surface
