"""UI Rendering Service - Centralized button and dialog drawing.

Responsibilities:
- Provides consistent, reusable UI element rendering
- Draws dialog boxes with borders and shadows
- Draws styled buttons with labels and colors
- No business logic, only presentation

Public API:
- draw_dialog(surface: pygame.Surface) -> None
      Renders a centered modal dialog box
      
- draw_button(
      surface: pygame.Surface,
      label: str,
      text_color: tuple[int,int,int],
      fill_color: tuple[int,int,int],
      x: int, y: int, w: int, h: int,
      rect: pygame.Rect | None = None
  ) -> None
      Renders a rounded button with centered text

Usage:
    # Draw a button
    draw_button(screen, "OK", (255,255,255), (0,128,0), 
                100, 200, 150, 40, button_rect)
    
    # Draw dialog background
    draw_dialog(screen)

Notes:
- Uses pygame.draw primitives for rendering
- Border radius = 6px for rounded corners
- Font: Arial 18pt for button labels
- Future: Consider theming system, DPI scaling
"""

from __future__ import annotations
import pygame
import logging
from typing import Tuple

log = logging.getLogger("crazycar.sim.screen")

# UI Style Constants
BUTTON_BORDER_RADIUS = 6  # Rounded corner radius in pixels
BUTTON_BORDER_WIDTH = 2  # Border thickness in pixels
BUTTON_BORDER_COLOR = (20, 20, 20)  # Dark border color
BUTTON_FONT_SIZE = 18  # Button label font size
BUTTON_FONT_NAME = "Arial"  # Button label font family


def draw_button(
    screen: pygame.Surface,
    label: str,
    text_color: Tuple[int, int, int],
    fill_color: Tuple[int, int, int],
    x: int, y: int, w: int, h: int,
    rect: pygame.Rect,
) -> None:
    """Draw a filled button with centered label.
    
    Args:
        screen: Pygame surface to draw on
        label: Button text to display
        text_color: RGB color for label text
        fill_color: RGB color for button background
        x: X coordinate (unused, rect is used)
        y: Y coordinate (unused, rect is used)
        w: Width (unused, rect is used)
        h: Height (unused, rect is used)
        rect: Pygame rect defining button bounds
        
    Note:
        Renders button to screen surface.
    """
    pygame.draw.rect(screen, fill_color, rect, border_radius=BUTTON_BORDER_RADIUS)
    # Subtle border
    pygame.draw.rect(screen, BUTTON_BORDER_COLOR, rect, width=BUTTON_BORDER_WIDTH, border_radius=BUTTON_BORDER_RADIUS)
    font = pygame.font.SysFont(BUTTON_FONT_NAME, BUTTON_FONT_SIZE)
    text_surf = font.render(label, True, text_color)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)


# Dialog Style Constants
DIALOG_OVERLAY_ALPHA = 120  # Transparency for background dimming
DIALOG_WIDTH = 500  # Dialog box width in pixels
DIALOG_HEIGHT = 200  # Dialog box height in pixels
DIALOG_BG_COLOR = (245, 245, 245)  # Light gray dialog background
DIALOG_BORDER_COLOR = (30, 30, 30)  # Dark border color
DIALOG_BORDER_RADIUS = 10  # Rounded corner radius
DIALOG_BORDER_WIDTH = 2  # Border thickness
DIALOG_TITLE_FONT_SIZE = 20  # Title font size
DIALOG_TITLE_TOP_PADDING = 16  # Padding from dialog top to title


def draw_dialog(screen: pygame.Surface) -> None:
    """Draw semi-transparent dialog overlay in screen center.
    
    Renders a modal dialog box with:
    - Semi-transparent black background (overlay)
    - Centered light gray dialog box
    - Rounded corners with dark border
    - Title text: "Change Mode?"
    
    Args:
        screen: Pygame surface to draw on
        
    Note:
        Blits overlay and dialog to screen.
        Compatible with Interface.draw_dialog signature.
    """
    w, h = screen.get_size()
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    # Darken background
    overlay.fill((0, 0, 0, DIALOG_OVERLAY_ALPHA))
    screen.blit(overlay, (0, 0))

    dialog_x = (w - DIALOG_WIDTH) // 2
    dialog_y = (h - DIALOG_HEIGHT) // 2
    dialog_rect = pygame.Rect(dialog_x, dialog_y, DIALOG_WIDTH, DIALOG_HEIGHT)

    # Dialog surface
    pygame.draw.rect(screen, DIALOG_BG_COLOR, dialog_rect, border_radius=DIALOG_BORDER_RADIUS)
    pygame.draw.rect(screen, DIALOG_BORDER_COLOR, dialog_rect, width=DIALOG_BORDER_WIDTH, border_radius=DIALOG_BORDER_RADIUS)

    # Title
    font = pygame.font.SysFont(BUTTON_FONT_NAME, DIALOG_TITLE_FONT_SIZE)
    title = font.render("Change Mode?", True, DIALOG_BORDER_COLOR)
    title_rect = title.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + DIALOG_TITLE_TOP_PADDING))
    screen.blit(title, title_rect)


def get_or_create_screen(size: tuple[int, int]) -> pygame.Surface:
    """Get existing pygame display or create a resizable one.
    
    Returns the current display surface if it exists, creating a new
    resizable window if needed. Resizes existing window if size mismatch.
    
    Args:
        size: Requested (width, height) in pixels
        
    Returns:
        Pygame display surface with RESIZABLE flag
        
    Note:
        May initialize pygame display or resize existing window.
        Centralizes display management previously in simulation.py.
    """
    scr = pygame.display.get_surface()
    if scr is None:
        scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    else:
        if scr.get_size() != size:
            scr = pygame.display.set_mode(size, pygame.RESIZABLE)
    return scr


# Debug Overlay Constants
DEBUG_BBOX_COLOR = (255, 200, 0)  # Yellow for bounding box
DEBUG_CENTERPOINT_COLOR = (0, 120, 255)  # Blue for centroid
DEBUG_CENTERPOINT_RADIUS = 6  # Centroid circle radius
DEBUG_DIRECTION_COLOR = (0, 200, 200)  # Cyan for direction line
DEBUG_SPAWN_COLOR = (0, 200, 0)  # Green for spawn point
DEBUG_SPAWN_RADIUS = 8  # Spawn point circle radius
DEBUG_SPAWN_ARROW_LENGTH = 24  # Arrow length for spawn direction
DEBUG_SPAWN_ARROW_WIDTH = 3  # Arrow line thickness
DEBUG_PIXEL_COLOR = (255, 0, 0)  # Red for sampled pixels
DEBUG_PIXEL_RADIUS = 2  # Sampled pixel marker radius
DEBUG_PIXEL_SAMPLE_COUNT = 30  # Max number of pixels to draw
DEBUG_MIN_LINE_LENGTH = 60  # Minimum direction line length


def draw_finish_debug(screen: pygame.Surface, info: dict) -> None:
    """Draw finish line detection debug overlay (if CRAZYCAR_DEBUG=1).
    
    Visualizes PCA-based finish line detection:
    - Yellow bounding box around finish pixels
    - Blue centroid marker
    - Cyan principal direction line (PCA eigenvector)
    - Green spawn point with arrow showing spawn direction
    - Red dots for sampled finish pixels
    
    Args:
        screen: Pygame surface to draw on
        info: Detection data from MapService.get_detect_info() containing:
              xs, ys: Pixel coordinates
              minx, maxx, miny, maxy: Bounding box
              cx, cy: Centroid
              vx, vy: Principal direction vector
              nx, ny: Normal vector (perpendicular to direction)
              sign: Direction sign (+1 or -1)
              spawn_x, spawn_y: Spawn position
              
    Note:
        Renders debug overlay to screen (only if CRAZYCAR_DEBUG=1).
        Best-effort rendering, silently catches exceptions.
        Skips drawing if environment variable not set.
    """
    import os
    
    # Only draw debug overlay if CRAZYCAR_DEBUG=1
    if os.getenv("CRAZYCAR_DEBUG", "0") != "1":
        return
    
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

        # Bounding box (yellow)
        pygame.draw.rect(screen, DEBUG_BBOX_COLOR, (minx, miny, maxx - minx + 1, maxy - miny + 1), 2)
        # Centroid (blue)
        pygame.draw.circle(screen, DEBUG_CENTERPOINT_COLOR, (int(cx), int(cy)), DEBUG_CENTERPOINT_RADIUS, 2)
        # Principal direction line (cyan)
        line_len = max(DEBUG_MIN_LINE_LENGTH, int(max(maxx - minx, maxy - miny)))
        x1 = int(cx - vx * line_len)
        y1 = int(cy - vy * line_len)
        x2 = int(cx + vx * line_len)
        y2 = int(cy + vy * line_len)
        pygame.draw.line(screen, DEBUG_DIRECTION_COLOR, (x1, y1), (x2, y2), 2)
        # Spawn point (green) with arrow in normal direction (spawn direction)
        pygame.draw.circle(screen, DEBUG_SPAWN_COLOR, (spawn_x, spawn_y), DEBUG_SPAWN_RADIUS)
        arrow_tip = (int(spawn_x + sign * nx * DEBUG_SPAWN_ARROW_LENGTH), int(spawn_y + sign * ny * DEBUG_SPAWN_ARROW_LENGTH))
        pygame.draw.line(screen, DEBUG_SPAWN_COLOR, (spawn_x, spawn_y), arrow_tip, DEBUG_SPAWN_ARROW_WIDTH)
        # Sample red pixels (red dots)
        for i in range(0, len(xs), max(1, len(xs)//DEBUG_PIXEL_SAMPLE_COUNT)):
            pygame.draw.circle(screen, DEBUG_PIXEL_COLOR, (xs[i], ys[i]), DEBUG_PIXEL_RADIUS)
    except Exception:
        # best-effort drawing
        return
