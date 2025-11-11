# =============================================================================
# crazycar/sim/map_service.py  —  Karte/Track laden, skalieren, blitten
# -----------------------------------------------------------------------------
# Aufgabe:
# - Lädt die Track-Grafik (z. B. "Racemap.png") aus dem Assets-Verzeichnis.
# - Skaliert auf aktuelle Fenstergröße; stellt blit(screen) bereit.
# - Reagiert auf Window-Resize via resize(new_size).
#
# Erweiterung:
# - get_spawn(): Liefert kartenabhängigen Spawn (Pixel) aus:
#     1) assets/maps.json (normierte Koordinaten 0..1), sonst
#     2) Auto-Detect aus roter Ziellinie (PCA), sonst
#     3) Fallback (alter fixer Spawn)
# - Detailliertes Logging, wo die rote Linie erkannt wurde (BBox, Schwerpunkt,
#   Richtung, Winkel, Spawn-Punkt).
#
# Öffentliche API:
# - class MapService:
#       __init__(window_size: tuple[int,int], asset_name: str = "Racemap.png")
#       resize(window_size: tuple[int,int]) -> None
#       blit(screen: pygame.Surface) -> None
#       surface -> pygame.Surface
#       map_name -> str
#       get_spawn(idx: int = 0) -> Spawn
# =============================================================================

from __future__ import annotations
import os
import math
import logging
from dataclasses import dataclass
from typing import Tuple, Optional

import pygame

log = logging.getLogger("crazycar.sim.map")

# -------------------------
# Konfig / Konstanten-Import
# -------------------------
try:
    from ..car.constants import (
        FINISH_LINE_COLOR,
        BORDER_COLOR,
        f as _F,
        CAR_cover_size,
    )
except Exception:
    # Fallbacks, falls constants nicht importierbar
    FINISH_LINE_COLOR = (237, 28, 36, 255)   # RGBA
    BORDER_COLOR = (255, 255, 255, 255)
    _F = 0.8
    CAR_cover_size = 32

# Toleranz für "Rot-Erkennung" (kann via ENV überschrieben werden)
_FINISH_TOL = int(os.getenv("CRAZYCAR_FINISH_TOL", "40"))

# Schrittweite für Fallback-Scan ohne surfarray/NumPy (Performance)
_SCAN_STEP = int(os.getenv("CRAZYCAR_SCAN_STEP", "2"))

@dataclass(frozen=True)
class Spawn:
    x_px: int
    y_px: int
    angle_deg: float = 0.0


# Note: maps.json/meta loader intentionally removed — MapService controls spawn


# =============================================================================
# MapService
# =============================================================================
class MapService:
    """
    Lädt die Racemap einmal (raw) und hält eine zur Fenstergröße skalierte Surface.
    - resize(new_size): skaliert aus dem Raw neu
    - blit(screen): zeichnet den aktuellen Map-Frame als Hintergrund
    - get_spawn(): bestimmt die Spawn-Position/Blickrichtung
    """
    def __init__(self, window_size: Tuple[int, int], asset_name: str = "Racemap.png") -> None:
        assets_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", asset_name))
        log.debug("Lade Map: %s", assets_path)
        # convert_alpha preserves per-pixel alpha and keeps colors intact
        try:
            self._raw = pygame.image.load(assets_path).convert_alpha()
        except Exception:
            # Falls convert_alpha auf dieser Plattform scheitert, fallback to convert
            self._raw = pygame.image.load(assets_path).convert()
        self._surface = pygame.transform.scale(self._raw, window_size)

        # Für Spawns/Metadaten
        self._asset_name = asset_name
        self._assets_dir = os.path.dirname(assets_path)
        self._meta_path = os.path.join(self._assets_dir, "maps.json")

        # Manuelle/überschriebene Spawn-Option (wird bevorzugt, wenn gesetzt)
        self._manual_spawn: Optional[Spawn] = None

        # Cache für Auto-Spawn (nur einmal pro Karte ermitteln)
        self._cached_spawn: Optional[Spawn] = None

    def resize(self, window_size: Tuple[int, int]) -> None:
        self._surface = pygame.transform.scale(self._raw, window_size)
        # Skalierung ändert Koordinaten — Auto-Spawn neu bestimmen
        self._cached_spawn = None

    def blit(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    @property
    def surface(self) -> pygame.Surface:
        """Aktuell skalierte Map-Surface (falls jemand direkten Zugriff braucht)."""
        return self._surface

    @property
    def map_name(self) -> str:
        """Eindeutiger Schlüssel für Karten-Metadaten (hier: Dateiname)."""
        return self._asset_name

    # -------------------------------------------------------------------------
    # Spawn API
    # -------------------------------------------------------------------------
    def get_spawn(self, idx: int = 0) -> Spawn:
        """
        Reihenfolge (keine maps.json-Nutzung):
          1) Manuell via `set_manual_spawn()` gesetzter Spawn
          2) Auto-Detect aus roter Ziellinie
          3) Fallback (alter fixer Spawn)
        """
        # 1) Manuell gesetzter Spawn?
        if self._manual_spawn is not None:
            log.info("Spawn (manuell) verwendet: %s", self._manual_spawn)
            return self._manual_spawn

        # 2) Auto-Detect (rote Ziellinie)
        if self._cached_spawn is None:
            self._cached_spawn = self._spawn_from_finish_line()
        if self._cached_spawn is not None:
            return self._cached_spawn

        # 3) Fallback (kompatibel zum bisherigen Verhalten)
        fx, fy = int(200 * _F), int(200 * _F)
        log.warning("Kein Spawn gefunden → Fallback (%d, %d) @ 0°.", fx, fy)
        return Spawn(fx, fy, 0.0)

    # -------------------------------------------------------------------------
    # Auto-Spawn aus roter Ziellinie
    # -------------------------------------------------------------------------
    def _spawn_from_finish_line(self) -> Optional[Spawn]:
        """
        Findet die rote Ziellinie (nahe FINISH_LINE_COLOR), bestimmt per PCA die
        Tangentialrichtung und setzt den Spawn leicht vor die Linie. Liefert Logs:
          - Anzahl rote Pixel, Bounding-Box, Schwerpunkt (cx,cy)
          - Tangentenrichtung, gewähltes Vorzeichen (Fahrtrichtung)
          - finaler Spawn (x,y) und Winkel (deg)
        """
        info = self._detect_finish_info()
        if not info or info.get("n", 0) < 6:
            log.debug("Finish-Line: zu wenige rote Pixel erkannt (n=%d).", 0 if not info else info.get("n", 0))
            return None

        spawn_x = info["spawn_x"]
        spawn_y = info["spawn_y"]
        angle_deg = info["angle_deg"]

        # Apply probe flip heuristic here so callers (e.g. simulation) receive
        # a Spawn whose angle already accounts for forward/back border checks.
        try:
            angle_deg = self._apply_probe_flip(spawn_x, spawn_y, angle_deg)
        except Exception:
            # best-effort only; do not fail spawn detection on probe errors
            pass

        log.info(
            "Auto-Spawn (Finish-Line): Spawn=(%d,%d) Winkel=%.1f°. Linienmitte=(%.1f,%.1f) Tangente=(%.3f,%.3f) Normale=(%.3f,%.3f) sign=%+d [score+%.1f/%.1f-].",
            spawn_x, spawn_y, angle_deg, info["cx"], info["cy"], info["vx"], info["vy"], info.get("nx", 0.0), info.get("ny", 0.0), info.get("sign", 0), info.get("s_pos", 0.0), info.get("s_neg", 0.0)
        )
        return Spawn(spawn_x, spawn_y, angle_deg)

    def _apply_probe_flip(self, spawn_x: int, spawn_y: int, map_angle: float) -> float:
        """
        Best-effort sampling in front of / behind the spawn to detect whether
        the computed normal points into the border (e.g. white). If forward is
        on average closer to the border than backward, flip the angle by 180°.
        Returns the (possibly flipped) map_angle in the same convention as
        returned by _detect_finish_info (degrees from atan2).
        """
        try:
            import math
            # CAR_cover_size and BORDER_COLOR are available from module imports
            probe_dist = max(8.0, float(CAR_cover_size) * 0.8)
            rad = math.radians(360.0 - float(map_angle))

            steps = [1, 2, 3]
            f_points = []
            b_points = []
            surf = self._surface
            w, h = surf.get_width(), surf.get_height()

            def sample(px, py):
                if px < 0 or py < 0 or px >= w or py >= h:
                    return None
                c = surf.get_at((px, py))
                return (int(c[0]), int(c[1]), int(c[2]))

            for s in steps:
                dx = math.cos(rad) * probe_dist * s
                dy = math.sin(rad) * probe_dist * s
                fx = int(round(spawn_x + dx))
                fy = int(round(spawn_y + dy))
                bx = int(round(spawn_x - dx))
                by = int(round(spawn_y - dy))
                fcol = sample(fx, fy)
                bcol = sample(bx, by)
                if fcol is not None:
                    f_points.append(((fx, fy), fcol))
                if bcol is not None:
                    b_points.append(((bx, by), bcol))

            def dist2(c):
                return (c[0]-BORDER_COLOR[0])**2 + (c[1]-BORDER_COLOR[1])**2 + (c[2]-BORDER_COLOR[2])**2

            df_sum = sum(dist2(c) for (_, c) in f_points) if f_points else float('inf')
            db_sum = sum(dist2(c) for (_, c) in b_points) if b_points else float('inf')

            log.debug("Spawn probes: forward=%d points back=%d points df_sum=%d db_sum=%d", len(f_points), len(b_points), int(df_sum), int(db_sum))

            # draw probe points on the surface for debug visibility (red=forward, green=back)
            try:
                for (px, py), _c in f_points:
                    pygame.draw.circle(surf, (255, 0, 0), (px, py), 3)
                for (px, py), _c in b_points:
                    pygame.draw.circle(surf, (0, 255, 0), (px, py), 3)
            except Exception:
                # drawing best-effort only
                pass

            if f_points and b_points and df_sum < db_sum:
                new_map = (float(map_angle) + 180.0) % 360.0
                log.info("Spawn angle flipped 180° (multi-sample): df_sum=%d db_sum=%d -> %.1f->%.1f", int(df_sum), int(db_sum), float(map_angle), new_map)
                return new_map
        except Exception:
            pass
        return float(map_angle)

    # Schneller Pixel-Collector via surfarray (NumPy); liefert (xs, ys) Listen
    def _collect_red_pixels_fast(self) -> tuple[Optional[list[int]], Optional[list[int]]]:
        # delegate to finish_detection fast collector
        from .finish_detection import collect_red_pixels_fast
        return collect_red_pixels_fast(self._surface, FINISH_LINE_COLOR[:3], _FINISH_TOL)

    # Fallback-Pixel-Collector ohne NumPy (langsamer, daher mit Schrittweite)
    def _collect_red_pixels_slow(self) -> tuple[list[int], list[int]]:
        from .finish_detection import collect_red_pixels_slow
        return collect_red_pixels_slow(self._surface, FINISH_LINE_COLOR[:3], _FINISH_TOL, _SCAN_STEP)

    # Wählt Vorzeichen der Tangente, indem entlang ±Vektor geprüft wird,
    # ob es eher Richtung Rand (weiß) geht (das wird bestraft).
    def _choose_forward_sign(self, cx: float, cy: float, vx: float, vy: float) -> tuple[int, float, float]:
        from .finish_detection import choose_forward_sign
        return choose_forward_sign(self._surface, cx, cy, vx, vy, BORDER_COLOR[:3])

    # -------------------------------------------------------------------------
    # Debug-Rendering: zeichnet erkannte Finish-Line-Informationen auf Surface
    # -------------------------------------------------------------------------
    def draw_finish_debug(self, screen: pygame.Surface) -> None:
        """
        Zeichnet BBox, Schwerpunkt, Hauptrichtung und den berechneten Spawn-Punkt
        auf die übergebene Surface. Nützlich zum Debuggen, wenn die rote Linie
        nicht erkannt wird oder Spawn-Positionen überprüft werden sollen.
        """
        # Delegate drawing to screen_service.draw_finish_debug which expects
        # a full detect_info dict (computed by get_detect_info).
        try:
            from .screen_service import draw_finish_debug as _sfd
            info = self.get_detect_info() or {"n": 0}
            if not info or info.get("n", 0) < 1:
                log.debug("draw_finish_debug: keine roten Pixel zum Zeichnen.")
                return
            _sfd(screen, info)
        except Exception as e:
            log.debug("draw_finish_debug: Fehler beim Delegieren an screen_service: %s", e)
            return

    # -------------------------------------------------------------------------
    # Detection helper & public control API
    # -------------------------------------------------------------------------
    def _detect_finish_info(self) -> dict | None:
        """Sammelt rote Pixel, berechnet BBox, Schwerpunkt, Hauptrichtung,
        Vorzeichen und den vorgeschlagenen Spawn. Liefert ein Dict mit allen
        relevanten Werten zur weiteren Auswertung/Logging.
        """
        try:
            xs, ys = self._collect_red_pixels_fast()
            if xs is None or ys is None:
                xs, ys = self._collect_red_pixels_slow()
        except Exception as e:
            log.debug("_detect_finish_info: Fehler beim Sammeln roter Pixel: %s", e)
            return None

        # Ignore stray pixels by selecting the largest connected red component
        from .finish_detection import select_largest_component
        xs, ys = select_largest_component(xs, ys)

        n = 0 if not xs else len(xs)
        if n < 1:
            return {"n": 0}

        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        # centroid as projection origin
        cx_mean = sum(xs) / n
        cy_mean = sum(ys) / n

        from .finish_detection import principal_direction
        vx, vy = principal_direction(xs, ys, cx_mean, cy_mean)
        # midpoint along tangent (better geometric center of the detected line)
        ts = [((x - cx_mean) * vx + (y - cy_mean) * vy) for x, y in zip(xs, ys)]
        tmin = min(ts)
        tmax = max(ts)
        tmid = 0.5 * (tmin + tmax)
        cx = cx_mean + tmid * vx
        cy = cy_mean + tmid * vy

        # Normale (für Spawn-Richtung)
        nx, ny = -vy, vx
        sign, s_pos, s_neg = self._choose_forward_sign(cx, cy, nx, ny)

        offset = max(20, int(1.5 * int(CAR_cover_size or 32)))
        spawn_x = int(cx + sign * nx * offset)
        spawn_y = int(cy + sign * ny * offset)
        # Blickrichtung des Fahrzeugs = Richtung der Normale (sign bestimmt Seite)
        angle_rad = math.atan2(sign * ny, sign * nx)
        angle_deg = math.degrees(angle_rad)

        info = {
            "n": n,
            "xs": xs,
            "ys": ys,
            "minx": minx,
            "maxx": maxx,
            "miny": miny,
            "maxy": maxy,
            "cx": cx,
            "cy": cy,
            "vx": vx,
            "vy": vy,
            "nx": nx,
            "ny": ny,
            "sign": sign,
            "s_pos": s_pos,
            "s_neg": s_neg,
            "spawn_x": spawn_x,
            "spawn_y": spawn_y,
            "angle_deg": angle_deg,
        }
        return info

    # largest-component selection moved to sim.finish_detection.select_largest_component

    def get_detect_info(self) -> dict:
        """Public wrapper to return detection information (useful for logging/tests)."""
        return self._detect_finish_info() or {"n": 0}

    def set_manual_spawn(self, spawn: Spawn) -> None:
        """Set a manual spawn that will be returned by `get_spawn()` with priority."""
        self._manual_spawn = spawn
        log.info("Manual spawn gesetzt: %s", spawn)

    def clear_manual_spawn(self) -> None:
        """Clear any manual spawn override and re-enable auto-detect."""
        self._manual_spawn = None
        log.info("Manual spawn gelöscht; Auto-Detect reaktiviert.")

    def set_finish_tolerance(self, tol: int) -> None:
        """Adjust the RGB tolerance used to detect the finish line (squared distance).
        This updates the module-level _FINISH_TOL used by collectors.
        """
        global _FINISH_TOL
        _FINISH_TOL = int(tol)
        # Invalidate cached detection
        self._cached_spawn = None
        log.info("Finish line tolerance gesetzt: %d", _FINISH_TOL)

    def force_redetect(self) -> Optional[Spawn]:
        """Forces re-detection of the finish line and returns the computed spawn (or None)."""
        self._cached_spawn = None
        res = self._spawn_from_finish_line()
        if res is None:
            log.info("force_redetect: keine Finish-Line erkannt.")
        else:
            log.info("force_redetect: ermittelter Spawn: %s", res)
        return res

# principal_direction moved to sim.finish_detection.principal_direction
