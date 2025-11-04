# =============================================================================
# crazycar/sim/screen_service.py  —  UI-Zeichnen (Buttons/Dialog)
# -----------------------------------------------------------------------------
# Aufgabe:
# - Zentralisiert das Zeichnen wiederkehrender UI-Elemente (Dialograhmen, Buttons).
# - Hält Rendering konsistent und testbar (keine Business-Logik).
#
# Öffentliche API:
# - draw_dialog(surface: pygame.Surface) -> None
# - draw_button(
#       surface: pygame.Surface,
#       label: str,
#       text_color: tuple[int,int,int],
#       fill_color: tuple[int,int,int],
#       x: int, y: int, w: int, h: int,
#       rect: pygame.Rect | None = None
#   ) -> None
#
# Hinweise:
# - Optionale Erweiterungen: HUD-Linien/Texthelpers, theming, DPI-Skalierung.
# =============================================================================

from __future__ import annotations
import pygame
import logging
from typing import Tuple

log = logging.getLogger("crazycar.sim.screen")

def draw_button(
    screen: pygame.Surface,
    label: str,
    text_color: Tuple[int, int, int],
    fill_color: Tuple[int, int, int],
    x: int, y: int, w: int, h: int,
    rect: pygame.Rect,
) -> None:
    """
    Zeichnet einen gefüllten Button mit zentriertem Label.
    Signatur kompatibel zu Interface.draw_button.
    """
    pygame.draw.rect(screen, fill_color, rect, border_radius=6)
    # leichte Kontur
    pygame.draw.rect(screen, (20, 20, 20), rect, width=2, border_radius=6)
    font = pygame.font.SysFont("Arial", 18)
    text_surf = font.render(label, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


def draw_dialog(screen: pygame.Surface) -> None:
    """
    Zeichnet einen halbtransparenten Dialog-Hintergrund (Overlay) in der Mitte.
    Signatur kompatibel zu Interface.draw_dialog (ohne weitere Args).
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    # Hintergrund abdunkeln
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, 0))

    dialog_w, dialog_h = 500, 200
    dialog_x = (w - dialog_w) // 2
    dialog_y = (h - dialog_h) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)

    # Dialogfläche
    pygame.draw.rect(screen, (245, 245, 245), dialog_rect, border_radius=10)
    pygame.draw.rect(screen, (30, 30, 30), dialog_rect, width=2, border_radius=10)

    # Titel
    font = pygame.font.SysFont("Arial", 20)
    title = font.render("Modus wechseln?", True, (20, 20, 20))
    title_rect = title.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + 16))
    screen.blit(title, title_rect)
