from __future__ import annotations
import math
import logging
from typing import List, Tuple
import pygame

log = logging.getLogger("crazycar.sim.finish_detection")

log = logging.getLogger("crazycar.sim.finish_detection")


def principal_direction(xs: List[int], ys: List[int], cx: float, cy: float) -> Tuple[float, float]:
    """Compute normalized principal direction (tangent) of a point cloud using PCA.
    
    Performs Principal Component Analysis analytically without NumPy by computing
    the covariance matrix and its eigenvectors. Used to determine the main orientation
    of the finish line from detected red pixels.
    
    Args:
        xs: List of x-coordinates of detected pixels
        ys: List of y-coordinates of detected pixels (must match len(xs))
        cx: Centroid x-coordinate
        cy: Centroid y-coordinate
        
    Returns:
        Tuple (vx, vy): Normalized unit vector representing principal direction.
                        Returns (1.0, 0.0) if input is empty.
    """
    # Fallback wenn keine Punkte vorhanden
    if not xs:
        return (1.0, 0.0)

    # Kovarianzmatrix berechnen: sxx, syy, sxy
    sxx = syy = sxy = 0.0
    n = float(len(xs))
    for x, y in zip(xs, ys):
        dx = x - cx
        dy = y - cy
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy

    # Normalisierung durch (n-1) für Stichproben-Kovarianz
    if n > 1:
        sxx /= (n - 1.0)
        syy /= (n - 1.0)
        sxy /= (n - 1.0)

    # Eigenwert berechnen: größter Eigenwert λ1 = (trace + √disc) / 2
    trace = sxx + syy
    det = sxx * syy - sxy * sxy
    disc = max(0.0, trace * trace - 4.0 * det)  # Diskriminante ≥ 0 sicherstellen
    sqrt_disc = math.sqrt(disc)
    l1 = 0.5 * (trace + sqrt_disc)

    # Eigenvektor zum größten Eigenwert: [sxy, λ1 - sxx]
    vx = sxy
    vy = l1 - sxx
    
    # Degenerierten Fall abfangen (alle Punkte identisch)
    EPSILON = 1e-12  # Numerische Toleranz für Nullvektoren
    if abs(vx) + abs(vy) < EPSILON:
        vx, vy = 1.0, 0.0

    # Auf Länge 1 normalisieren
    nrm = math.hypot(vx, vy) or 1.0
    vx /= nrm
    vy /= nrm
    return (vx, vy)


def select_largest_component(xs: List[int] | None, ys: List[int] | None) -> Tuple[List[int], List[int]]:
    """Find the largest 4-connected component in a set of pixel coordinates.
    
    Uses flood-fill algorithm to identify connected regions and returns only the
    largest component. This filters out isolated red pixels or noise that might
    not be part of the actual finish line.
    
    Args:
        xs: List of x-coordinates (can be None)
        ys: List of y-coordinates (can be None)
        
    Returns:
        Tuple (xs_out, ys_out): Coordinates of largest component, or ([], []) if empty.
    """
    # Eingabe validieren
    if not xs or not ys:
        return ([], [])

    # Set für schnelle Nachbarschaftssuche
    coords = set(zip(xs, ys))
    if not coords:
        return ([], [])

    best_comp = None
    best_size = 0
    # 4-Nachbarschaft (oben, unten, links, rechts)
    NEIGHBORS_4_CONNECTED = ((1, 0), (-1, 0), (0, 1), (0, -1))

    # Flood-Fill: Durchlaufe alle Komponenten
    while coords:
        start = coords.pop()
        comp = [start]
        queue = [start]
        
        # Breitensuche für aktuelle Komponente
        while queue:
            x0, y0 = queue.pop()
            for dx, dy in NEIGHBORS_4_CONNECTED:
                nx, ny = x0 + dx, y0 + dy
                if (nx, ny) in coords:
                    coords.remove((nx, ny))
                    queue.append((nx, ny))
                    comp.append((nx, ny))
        
        # Größte Komponente merken
        if len(comp) > best_size:
            best_size = len(comp)
            best_comp = comp

    if not best_comp:
        return ([], [])

    xs_out = [c[0] for c in best_comp]
    ys_out = [c[1] for c in best_comp]
    log.debug("Finish-Line: selected largest red component size=%d", len(xs_out))
    return xs_out, ys_out


def collect_red_pixels_fast(surface: "pygame.Surface", target_rgb: Tuple[int, int, int], tol: int) -> tuple[list[int] | None, list[int] | None]:
    """Fast pixel collection using NumPy vectorization (if available).
    
    Uses pygame.surfarray.pixels3d for efficient batch processing. Falls back
    to slow method if NumPy is not available.
    
    Args:
        surface: Pygame surface to scan
        target_rgb: Target color as (R, G, B) tuple
        tol: Color tolerance (Euclidean distance threshold)
        
    Returns:
        Tuple (xs, ys): Lists of matching pixel coordinates, or
                        ([], []) if no pixels found, or
                        (None, None) if NumPy unavailable.
    """
    try:
        import numpy as np  # type: ignore
        arr = pygame.surfarray.pixels3d(surface).copy()
        R0, G0, B0 = target_rgb
        dif = arr.astype(int) - np.array([[[R0, G0, B0]]], dtype=int)
        dist2 = (dif * dif).sum(axis=2)
        mask = dist2 <= (tol * tol)
        if not mask.any():
            return ([], [])
        ys, xs = np.where(mask.T)
        xs = xs.tolist()
        ys = ys.tolist()
        if xs and ys:
            log.debug("Finish-Line (fast): rote Pixel ~ %d, Beispielpunkte: (%d,%d), (%d,%d)", len(xs), xs[0], ys[0], xs[min(5, len(xs)-1)], ys[min(5, len(ys)-1)])
        return (xs, ys)
    except Exception as e:
        log.debug("Finish-Line (fast) nicht verfügbar: %s", e)
        return (None, None)


def collect_red_pixels_slow(surface: "pygame.Surface", target_rgb: Tuple[int, int, int], tol: int, step: int) -> tuple[list[int], list[int]]:
    """Fallback pixel collection without NumPy using manual iteration.
    
    Scans the surface pixel-by-pixel with configurable step size for performance.
    Always returns lists (possibly empty), never None.
    
    Args:
        surface: Pygame surface to scan
        target_rgb: Target color as (R, G, B) tuple
        tol: Color tolerance (Euclidean distance threshold)
        step: Pixel step size (e.g., 2 = every 2nd pixel for 4x speedup)
        
    Returns:
        Tuple (xs, ys): Lists of matching pixel coordinates (may be empty).
    """
    w, h = surface.get_width(), surface.get_height()
    xs: list[int] = []
    ys: list[int] = []

    # Quadrierte Toleranz für schnelleren Vergleich (vermeidet sqrt)
    tol2 = tol * tol

    # Surface locken für thread-sicheren Zugriff
    surface.lock()
    try:
        for y in range(0, h, step):
            for x in range(0, w, step):
                r, g, b, *_ = surface.get_at((x, y))
                dr = r - target_rgb[0]
                dg = g - target_rgb[1]
                db = b - target_rgb[2]
                if (dr * dr + dg * dg + db * db) <= tol2:
                    xs.append(x)
                    ys.append(y)
    finally:
        surface.unlock()

    log.debug("Finish-Line (slow): rote Pixel ~ %d (step=%d).", len(xs), step)
    return (xs, ys)


def choose_forward_sign(surface: "pygame.Surface", cx: float, cy: float, vx: float, vy: float, border_rgb: Tuple[int, int, int], sample_start: int = 8, sample_end: int = 80, sample_step: int = 4) -> tuple[int, float, float]:
    """Determine correct sign (+1 or -1) for tangent vector by sampling along both directions.
    
    Samples pixels along +direction and -direction from center point. Direction that
    encounters more border pixels (white) is penalized. This ensures the tangent
    points into the track, not toward the border.
    
    Args:
        surface: Pygame surface to sample from
        cx, cy: Center point coordinates
        vx, vy: Tangent vector components (not necessarily normalized)
        border_rgb: Border color to detect (typically white)
        sample_start: Start distance for sampling (pixels from center)
        sample_end: End distance for sampling (pixels from center)
        sample_step: Step size between samples (pixels)
        
    Returns:
        Tuple (sign, score_positive, score_negative): 
            - sign: +1 or -1 for chosen direction
            - score_positive: Penalty score for +direction
            - score_negative: Penalty score for -direction
    """
    w, h = surface.get_width(), surface.get_height()

    # Scoring-Funktion: Bestraft Richtung, die zu Rand zeigt
    def score(sign: int) -> float:
        """Berechnet Penalty-Score für gegebene Richtung (+1 oder -1)."""
        s = 0.0
        for k in range(sample_start, sample_end, sample_step):
            x = int(cx + sign * vx * k)
            y = int(cy + sign * vy * k)
            
            # Out-of-bounds = hohe Strafe (vermutlich Richtung Kartenrand)
            OUT_OF_BOUNDS_PENALTY = 10.0
            if x < 0 or y < 0 or x >= w or y >= h:
                s += OUT_OF_BOUNDS_PENALTY
                continue
            
            # Farbe prüfen: Weiß (Rand) = Strafe
            r, g, b, *_ = surface.get_at((x, y))
            dr = r - border_rgb[0]
            dg = g - border_rgb[1]
            db = b - border_rgb[2]
            
            # Toleranz 60 Pixel für "nah an weiß" (60² = 3600)
            BORDER_COLOR_TOLERANCE_SQ = 60 * 60
            if (dr * dr + dg * dg + db * db) < BORDER_COLOR_TOLERANCE_SQ:
                s += 1.0  # Strafe pro Rand-Pixel
        return s

    s_pos = score(+1)
    s_neg = score(-1)
    sign = +1 if s_pos <= s_neg else -1
    log.debug("Finish-Line: score(+)=%.1f, score(-)=%.1f → sign=%+d.", s_pos, s_neg, sign)
    return sign, s_pos, s_neg
