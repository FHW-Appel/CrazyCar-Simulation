# src/crazycar/sim/services/map_service.py
from __future__ import annotations
import os
from typing import Tuple, Optional
import pygame


class MapService:
    """
    Lädt und verwaltet die Rennstrecken-Map (z. B. assets/Racemap.png).
    - Keine pygame-Initialisierung auf Modulebene.
    - Konvertiert Surfaces nur, wenn bereits ein Display existiert (kein Crash im Headless).
    - Stellt die aktuell auf Fenstergröße skalierte Surface bereit.
    """

    def __init__(self, window_size: Tuple[int, int], path: Optional[str] = None) -> None:
        self._path = path or self._find_default_path()
        self._raw: Optional[pygame.Surface] = None        # Originalgröße
        self._scaled: Optional[pygame.Surface] = None     # Auf window_size skaliert
        self._raw_size: Optional[Tuple[int, int]] = None

        self._load_raw()
        self.rescale(window_size)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def path(self) -> str:
        return self._path

    @property
    def raw_size(self) -> Optional[Tuple[int, int]]:
        return self._raw_size

    def surface(self) -> pygame.Surface:
        """Gibt die auf Fenstergröße skalierte Map zurück."""
        if self._scaled is None:
            raise RuntimeError("MapService: scaled surface not prepared yet.")
        return self._scaled

    def rescale(self, window_size: Tuple[int, int]) -> pygame.Surface:
        """Map auf neue Fenstergröße skalieren."""
        if self._raw is None:
            raise RuntimeError("MapService: raw surface not loaded.")
        w, h = int(window_size[0]), int(window_size[1])
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid window size: {window_size}")
        # smoothscale wenn möglich, sonst scale
        scaler = getattr(pygame.transform, "smoothscale", pygame.transform.scale)
        scaled = scaler(self._raw, (w, h))
        self._scaled = self._maybe_convert(scaled)
        return self._scaled

    def reload(self, new_path: Optional[str] = None, window_size: Optional[Tuple[int, int]] = None) -> None:
        """
        Map neu laden (z. B. anderes Bild). Optional direkt rescalen.
        """
        if new_path:
            self._path = new_path
        self._load_raw()
        if window_size:
            self.rescale(window_size)
        else:
            # Wenn keine Größe angegeben, liefere unskaliert (falls Display existiert, konvertiert)
            self._scaled = self._maybe_convert(self._raw.copy())

    def draw_bg(self, screen: pygame.Surface, dest: Tuple[int, int] = (0, 0)) -> None:
        """
        Bequeme Helfer-Methode: skaliertes Map-Bild auf den Screen blitten.
        """
        screen.blit(self.surface(), dest)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _load_raw(self) -> None:
        if not os.path.exists(self._path):
            raise FileNotFoundError(
                f"Map image not found: {self._path}\n"
                f"Setze einen gültigen Pfad oder lege die Datei an."
            )
        # Achtung: convert()/convert_alpha() nur, wenn bereits ein Display gesetzt ist.
        img = pygame.image.load(self._path)
        self._raw = self._maybe_convert(img)
        self._raw_size = self._raw.get_size()

    def _maybe_convert(self, surf: pygame.Surface) -> pygame.Surface:
        """
        Konvertiert nur, wenn bereits ein Display existiert – sonst unverändert lassen.
        Das vermeidet 'No video mode has been set'.
        """
        try:
            if pygame.display.get_surface() is not None:
                # Ohne Alpha reicht convert(); falls du Transparenz brauchst: convert_alpha()
                return surf.convert()
        except pygame.error:
            pass
        return surf

    def _find_default_path(self) -> str:
        """
        Sucht gängige Default-Pfade relativ zu diesem Modul:
        - .../crazycar/assets/Racemap.png
        - .../crazycar/sim/assets/Racemap.png (Fallback)
        - .../crazycar/sim/Racemap.png (Fallback)
        """
        here = os.path.dirname(__file__)
        candidates = [
            os.path.normpath(os.path.join(here, "..", "..", "assets", "Racemap.png")),  # crazycar/assets
            os.path.normpath(os.path.join(here, "..", "assets", "Racemap.png")),        # sim/assets
            os.path.normpath(os.path.join(here, "..", "Racemap.png")),                  # sim/
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        # Nichts gefunden → nimm den ersten als "intentional default" und erlaube _load_raw() zu failen.
        return candidates[0]
