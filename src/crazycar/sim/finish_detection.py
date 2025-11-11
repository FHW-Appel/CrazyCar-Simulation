from __future__ import annotations
import math
import logging
from typing import List, Tuple
import pygame

log = logging.getLogger("crazycar.sim.finish_detection")

log = logging.getLogger("crazycar.sim.finish_detection")


def principal_direction(xs: List[int], ys: List[int], cx: float, cy: float) -> Tuple[float, float]:
    """
    Return normalized principal direction (vx, vy) of the point cloud (tangent).
    Computes covariance and eigenvector analytically (no NumPy required).
    """
    if not xs:
        return (1.0, 0.0)

    sxx = syy = sxy = 0.0
    n = float(len(xs))
    for x, y in zip(xs, ys):
        dx = x - cx
        dy = y - cy
        sxx += dx * dx
        syy += dy * dy
        sxy += dx * dy

    if n > 1:
        sxx /= (n - 1.0)
        syy /= (n - 1.0)
        sxy /= (n - 1.0)

    trace = sxx + syy
    det = sxx * syy - sxy * sxy
    disc = max(0.0, trace * trace - 4.0 * det)
    sqrt_disc = math.sqrt(disc)
    l1 = 0.5 * (trace + sqrt_disc)

    vx = sxy
    vy = l1 - sxx
    if abs(vx) + abs(vy) < 1e-12:
        vx, vy = 1.0, 0.0

    nrm = math.hypot(vx, vy) or 1.0
    vx /= nrm
    vy /= nrm
    return (vx, vy)


def select_largest_component(xs: List[int] | None, ys: List[int] | None) -> Tuple[List[int], List[int]]:
    """
    Given lists of x/y pixel coordinates, find the largest 4-connected
    component and return its coordinates. Filters out stray red pixels.
    """
    if not xs or not ys:
        return ([], [])

    coords = set(zip(xs, ys))
    if not coords:
        return ([], [])

    best_comp = None
    best_size = 0
    neigh = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while coords:
        start = coords.pop()
        comp = [start]
        queue = [start]
        while queue:
            x0, y0 = queue.pop()
            for dx, dy in neigh:
                nx, ny = x0 + dx, y0 + dy
                if (nx, ny) in coords:
                    coords.remove((nx, ny))
                    queue.append((nx, ny))
                    comp.append((nx, ny))
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
    """
    Fast pixel collector using numpy via pygame.surfarray.pixels3d.
    Returns (xs, ys) lists on success, ([],[]) if no pixels found, or (None,None)
    if the fast path is not available.
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
    """
    Fallback pixel collector without numpy. Scans with given step.
    Always returns (xs, ys) (possibly empty).
    """
    w, h = surface.get_width(), surface.get_height()
    xs: list[int] = []
    ys: list[int] = []

    tol2 = tol * tol

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
    """
    Wählt Vorzeichen der Tangente, indem entlang ±Vektor geprüft wird,
    ob es eher Richtung Rand (weiß) geht (wird bestraft). Returns (sign, s_pos, s_neg).
    """
    w, h = surface.get_width(), surface.get_height()

    def score(sign: int) -> float:
        s = 0.0
        for k in range(sample_start, sample_end, sample_step):
            x = int(cx + sign * vx * k)
            y = int(cy + sign * vy * k)
            if x < 0 or y < 0 or x >= w or y >= h:
                s += 10.0
                continue
            r, g, b, *_ = surface.get_at((x, y))
            dr = r - border_rgb[0]
            dg = g - border_rgb[1]
            db = b - border_rgb[2]
            if (dr * dr + dg * dg + db * db) < (60 * 60):
                s += 1.0
        return s

    s_pos = score(+1)
    s_neg = score(-1)
    sign = +1 if s_pos <= s_neg else -1
    log.debug("Finish-Line: score(+)=%.1f, score(-)=%.1f → sign=%+d.", s_pos, s_neg, sign)
    return sign, s_pos, s_neg
