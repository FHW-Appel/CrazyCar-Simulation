# src/crazycar/sim/services/screen_service.py
from __future__ import annotations
from typing import Tuple, Optional
import logging
import os
import pygame

log = logging.getLogger("crazycar.sim.screen")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("CRAZYCAR_DEBUG") == "1" else logging.INFO,
        format="%(asctime)s %(levelname)s [crazycar.screen] %(message)s",
    )


class ScreenService:
    """
    Verwaltet das Pygame-Display-Fenster:
    - Initialisiert Pygame erst hier (nicht auf Modulebene)
    - Erzeugt/holt die Surface (verhindert Doppel-Fenster)
    - Sauberes Resize auf neue Fenstergröße
    - Headless-Unterstützung via SDL_VIDEODRIVER=dummy
    """

    def __init__(
        self,
        size: Tuple[int, int],
        *,
        resizable: bool = True,
        caption: Optional[str] = None,
    ) -> None:
        self._flags = pygame.RESIZABLE if resizable else 0
        self._ensure_pygame_init()
        self._screen = self._get_or_create(size)
        if caption:
            try:
                pygame.display.set_caption(caption)
            except Exception:
                log.debug("Konnte Caption nicht setzen (headless?): %s", caption)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def screen(self) -> pygame.Surface:
        return self._screen

    def get_size(self) -> Tuple[int, int]:
        return self._screen.get_size()

    def resize(self, size: Tuple[int, int]) -> pygame.Surface:
        w, h = int(size[0]), int(size[1])
        if w <= 0 or h <= 0:
            raise ValueError(f"Invalid window size: {size}")
        log.debug("Resize → %s", (w, h))
        self._screen = pygame.display.set_mode((w, h), self._flags)
        return self._screen

    def set_caption(self, text: str) -> None:
        try:
            pygame.display.set_caption(text)
        except Exception:
            log.debug("set_caption() ignoriert (headless?): %s", text)

    def set_icon(self, surface: pygame.Surface) -> None:
        """Optional: App-Icon setzen (ignoriert, falls headless)."""
        try:
            pygame.display.set_icon(surface)
        except Exception:
            log.debug("set_icon() ignoriert (headless?)")

    @property
    def is_headless(self) -> bool:
        return os.environ.get("SDL_VIDEODRIVER", "") == "dummy"

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _ensure_pygame_init(self) -> None:
        if not pygame.get_init():
            # Hinweis: Für Headless-Tests vorher SDL_VIDEODRIVER=dummy setzen.
            pygame.init()
            log.debug("pygame.init()")

    def _get_or_create(self, size: Tuple[int, int]) -> pygame.Surface:
        scr = pygame.display.get_surface()
        if scr is None:
            log.debug("Kein aktives Display → set_mode(%s)", size)
            scr = pygame.display.set_mode(size, self._flags)
        else:
            if scr.get_size() != size:
                log.debug("Aktives Display %s → Resize auf %s", scr.get_size(), size)
                scr = pygame.display.set_mode(size, self._flags)
        return scr
