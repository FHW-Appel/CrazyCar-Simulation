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


def get_or_create_screen(size: tuple[int, int]) -> pygame.Surface:
    """
    Return existing pygame display surface or create a new resizable one
    with the requested size. This mirrors the helper previously in
    `simulation.py` and centralizes UI helpers in `screen_service`.
    """
    scr = pygame.display.get_surface()
    if scr is None:
        scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    else:
        if scr.get_size() != size:
            scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    return scr


def draw_finish_debug(screen: pygame.Surface, info: dict) -> None:
    """
    Draw finish-line detection overlay based on the detect_info dict returned
    by `MapService.get_detect_info()`.
    Expected keys in `info`: xs, ys, minx, maxx, miny, maxy, cx, cy, vx, vy,
    nx, ny, sign, spawn_x, spawn_y
    """
    try:
        xs = info.get("xs", []) or []
        ys = info.get("ys", []) or []
        if not xs or not ys:
            return

        minx = info.get("minx", min(xs))
        maxx = info.get("maxx", max(xs))
        miny = info.get("miny", min(ys))
        maxy = info.get("maxy", max(ys))
        cx = info.get("cx", sum(xs)/len(xs))
        cy = info.get("cy", sum(ys)/len(ys))
        vx = info.get("vx", 1.0)
        vy = info.get("vy", 0.0)
        nx = info.get("nx", -vy)
        ny = info.get("ny", vx)
        sign = info.get("sign", 1)
        spawn_x = int(info.get("spawn_x", int(cx)))
        spawn_y = int(info.get("spawn_y", int(cy)))

        YELLOW = (255, 200, 0)
        CYAN = (0, 200, 200)
        BLUE = (0, 120, 255)
        GREEN = (0, 200, 0)
        RED = (255, 0, 0)

        # Bounding-Box (gelb)
        pygame.draw.rect(screen, YELLOW, (minx, miny, maxx - minx + 1, maxy - miny + 1), 2)
        # Schwerpunkt (blau)
        pygame.draw.circle(screen, BLUE, (int(cx), int(cy)), 6, 2)
        # Hauptrichtungslinie (cyan)
        line_len = max(60, int(max(maxx - minx, maxy - miny)))
        x1 = int(cx - vx * line_len)
        y1 = int(cy - vy * line_len)
        x2 = int(cx + vx * line_len)
        y2 = int(cy + vy * line_len)
        pygame.draw.line(screen, CYAN, (x1, y1), (x2, y2), 2)
        # Spawn-Punkt (grün) und ein kleiner Pfeil in Normal-Richtung (Fahrtrichtung)
        pygame.draw.circle(screen, GREEN, (spawn_x, spawn_y), 8)
        arrow_tip = (int(spawn_x + sign * nx * 24), int(spawn_y + sign * ny * 24))
        pygame.draw.line(screen, GREEN, (spawn_x, spawn_y), arrow_tip, 3)
        # Markiere rote Pixel-Beispiel (rot, punktuell)
        for i in range(0, len(xs), max(1, len(xs)//30)):
            pygame.draw.circle(screen, RED, (xs[i], ys[i]), 2)
    except Exception:
        # best-effort drawing
        return
