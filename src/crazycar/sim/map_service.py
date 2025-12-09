"""Map Service - Track loading, scaling, and spawn detection.

Responsibilities:
- Load track graphics (e.g., "Racemap.png") from assets directory
- Scale to current window size, provide blit(screen) rendering
- React to window resize via resize(new_size)
- Detect spawn position and direction from red finish line (PCA)

Extensions:
- get_spawn(): Returns map-dependent spawn (pixels) from:
    1) Manual override via set_manual_spawn(), else
    2) Auto-detect from red finish line (PCA algorithm), else
    3) Fallback to legacy fixed spawn (200, 200)
- Detailed logging: Red line detection (bbox, centroid, direction, angle, spawn point)

Public API:
- class MapService:
      __init__(window_size: tuple[int,int], asset_name: str = "Racemap.png")
      
      resize(window_size: tuple[int,int]) -> None:
          Rescale map to new window dimensions
          
      blit(screen: pygame.Surface) -> None:
          Draw map as background
          
      surface -> pygame.Surface:
          Currently scaled map surface (read-only property)
          
      map_name -> str:
          Asset filename for metadata lookup
          
      get_spawn(idx: int = 0) -> Spawn:
          Get spawn position and heading angle
          Returns Spawn(x_px, y_px, angle_deg)
          
      set_manual_spawn(spawn: Spawn | None) -> None:
          Override auto-detection with manual spawn
          
      get_detect_info() -> dict:
          Debug information about finish line detection
          (for debug overlay rendering)

Auto-Detection Algorithm:
1. Scan map surface for red pixels (FINISH_LINE_COLOR ± tolerance)
2. If < 10 pixels found: Fall back to legacy spawn
3. Otherwise: Apply PCA (Principal Component Analysis)
   - Calculate centroid (cx, cy)
   - Find bounding box (minx, maxx, miny, maxy)
   - Compute covariance matrix, find eigenvectors
   - Primary eigenvector = finish line direction
   - Perpendicular = spawn direction (forward from line)
   - Choose sign so spawn points "into" the track
4. Spawn position = centroid + small offset in spawn direction

Usage:
    map_service = MapService((1920, 1080), "Racemap.png")
    map_service.blit(screen)
    
    spawn = map_service.get_spawn()
    car.set_position((spawn.x_px, spawn.y_px))
    car.carangle = spawn.angle_deg
    
    # Manual override
    map_service.set_manual_spawn(Spawn(300, 300, 45.0))

Notes:
- Red finish line color: (237, 28, 36, 255) RGBA
- Tolerance: ±40 per channel (configurable via CRAZYCAR_FINISH_TOL)
- Scan step: Every 2 pixels (configurable via CRAZYCAR_SCAN_STEP)
- Uses pygame.surfarray if available (NumPy), else fallback pixel loop
- PCA requires at least 10 red pixels for stability
- Debug overlay: Set CRAZYCAR_DEBUG=1 to visualize detection
"""

from __future__ import annotations
import os
import math
import logging
from dataclasses import dataclass
from typing import Tuple, Optional

import pygame

log = logging.getLogger("crazycar.sim.map")

# -------------------------
# Config / Constants Import
# -------------------------
try:
    from ..car.constants import (
        FINISH_LINE_COLOR,
        BORDER_COLOR,
        f as _F,
        CAR_cover_size,
    )
except Exception:
    # Fallbacks if constants not importable
    FINISH_LINE_COLOR = (237, 28, 36, 255)   # RGBA
    BORDER_COLOR = (255, 255, 255, 255)
    _F = 0.8
    CAR_cover_size = 32

# Tolerance for red detection (overridable via ENV)
_FINISH_TOL = int(os.getenv("CRAZYCAR_FINISH_TOL", "40"))

# Step size for fallback scan without surfarray/NumPy (performance)
_SCAN_STEP = int(os.getenv("CRAZYCAR_SCAN_STEP", "2"))


@dataclass(frozen=True)
class Spawn:
    """Spawn point with position and heading angle."""
    x_px: int
    y_px: int
    angle_deg: float = 0.0


# Note: maps.json/meta loader intentionally removed — MapService controls spawn


# =============================================================================
# MapService
# =============================================================================
class MapService:
    """Loads racemap once (raw) and maintains window-scaled surface.
    
    - resize(new_size): Rescales from raw image
    - blit(screen): Draws current map frame as background
    - get_spawn(): Determines spawn position/direction
    """
    def __init__(self, window_size: Tuple[int, int], asset_name: str = "Racemap.png") -> None:
        assets_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", asset_name))
        log.debug("Lade Map: %s", assets_path)
        # convert_alpha preserves per-pixel alpha and keeps colors intact
        try:
            self._raw = pygame.image.load(assets_path).convert_alpha()
        except Exception:
            # If convert_alpha fails on this platform, fallback to convert
            self._raw = pygame.image.load(assets_path).convert()
        self._surface = pygame.transform.scale(self._raw, window_size)

        # For spawns/metadata
        self._asset_name = asset_name
        self._assets_dir = os.path.dirname(assets_path)
        self._meta_path = os.path.join(self._assets_dir, "maps.json")

        # Manual/overridden spawn option (preferred if set)
        self._manual_spawn: Optional[Spawn] = None

        # Cache for auto-spawn (determine only once per map)
        self._cached_spawn: Optional[Spawn] = None

    def resize(self, window_size: Tuple[int, int]) -> None:
        self._surface = pygame.transform.scale(self._raw, window_size)
        # Scaling changes coordinates — redetermine auto-spawn
        self._cached_spawn = None

    def blit(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    @property
    def surface(self) -> pygame.Surface:
        """Currently scaled map surface (if direct access is needed)."""
        return self._surface

    @property
    def map_name(self) -> str:
        """Unique key for map metadata (here: filename)."""
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
          - Tangent direction, chosen sign (driving direction)
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

        log.debug(
            "Auto-Spawn (Finish-Line): Spawn=(%d,%d) Winkel=%.1f°. Linienmitte=(%.1f,%.1f) Tangente=(%.3f,%.3f) Normale=(%.3f,%.3f) sign=%+d [score+%.1f/%.1f-].",
            spawn_x, spawn_y, angle_deg, info["cx"], info["cy"], info["vx"], info["vy"], info.get("nx", 0.0), info.get("ny", 0.0), info.get("sign", 0), info.get("s_pos", 0.0), info.get("s_neg", 0.0)
        )
        return Spawn(spawn_x, spawn_y, angle_deg)

    def _apply_probe_flip(self, spawn_x: int, spawn_y: int, map_angle: float) -> float:
        """Detect if spawn angle points toward border and flip by 180° if necessary.
        
        Samples multiple points in front of and behind the spawn position. If forward
        direction has more border-colored pixels than backward, the angle is flipped.
        This ensures the vehicle starts facing into the track, not toward the wall.
        
        Args:
            spawn_x: Spawn x-coordinate (pixels)
            spawn_y: Spawn y-coordinate (pixels)
            map_angle: Initial angle from finish-line detection (degrees)
            
        Returns:
            Float: Possibly flipped angle in same convention as input (atan2 degrees).
        """
        try:
            import math
            
            # Probe distance: Minimum 8px, or 80% of car size (whichever is larger)
            MIN_PROBE_DISTANCE = 8.0
            PROBE_DISTANCE_FACTOR = 0.8  # 80% of car size
            probe_dist = max(MIN_PROBE_DISTANCE, float(CAR_cover_size) * PROBE_DISTANCE_FACTOR)
            
            # Winkel in Pygame-Konvention umrechnen
            rad = math.radians(360.0 - float(map_angle))

            # 3 Probe-Punkte in jede Richtung (1x, 2x, 3x Distanz)
            PROBE_STEPS = [1, 2, 3]
            f_points = []  # Forward-Richtung Samples
            b_points = []  # Backward-Richtung Samples
            surf = self._surface
            w, h = surf.get_width(), surf.get_height()

            def sample(px, py):
                """Sample color at position (px, py), None if out of bounds."""
                if px < 0 or py < 0 or px >= w or py >= h:
                    return None
                c = surf.get_at((px, py))
                return (int(c[0]), int(c[1]), int(c[2]))

            # Probe-Punkte in beide Richtungen samplen
            for s in PROBE_STEPS:
                dx = math.cos(rad) * probe_dist * s
                dy = math.sin(rad) * probe_dist * s
                
                # Forward-Punkt (in Fahrtrichtung)
                fx = int(round(spawn_x + dx))
                fy = int(round(spawn_y + dy))
                
                # Backward-Punkt (entgegen Fahrtrichtung)
                bx = int(round(spawn_x - dx))
                by = int(round(spawn_y - dy))
                
                fcol = sample(fx, fy)
                bcol = sample(bx, by)
                
                if fcol is not None:
                    f_points.append(((fx, fy), fcol))
                if bcol is not None:
                    b_points.append(((bx, by), bcol))

            # Calculate color distance to border (squared for performance)
            def dist2(c):
                """Squared Euclidean distance to border color."""
                return (c[0]-BORDER_COLOR[0])**2 + (c[1]-BORDER_COLOR[1])**2 + (c[2]-BORDER_COLOR[2])**2

            # Sum of distances: Lower = closer to border
            df_sum = sum(dist2(c) for (_, c) in f_points) if f_points else float('inf')
            db_sum = sum(dist2(c) for (_, c) in b_points) if b_points else float('inf')

            log.debug("Spawn probes: forward=%d points back=%d points df_sum=%d db_sum=%d", len(f_points), len(b_points), int(df_sum), int(db_sum))

            # Debug visualization: Draw probe points on map (red=forward, green=backward)
            # Only if CRAZYCAR_DEBUG=1 is set
            if os.getenv("CRAZYCAR_DEBUG", "0") == "1":
                try:
                    DEBUG_MARKER_RADIUS = 3  # Radius of debug circles in pixels
                    for (px, py), _c in f_points:
                        pygame.draw.circle(surf, (255, 0, 0), (px, py), DEBUG_MARKER_RADIUS)  # Red = Forward
                    for (px, py), _c in b_points:
                        pygame.draw.circle(surf, (0, 255, 0), (px, py), DEBUG_MARKER_RADIUS)  # Green = Backward
                except Exception:
                    # Best-effort drawing: Ignore errors
                    pass

            # Decision: If forward closer to border than backward → rotate 180°
            if f_points and b_points and df_sum < db_sum:
                FLIP_ANGLE = 180.0
                new_map = (float(map_angle) + FLIP_ANGLE) % 360.0
                log.debug("Spawn angle flipped 180° (multi-sample): df_sum=%d db_sum=%d -> %.1f->%.1f", int(df_sum), int(db_sum), float(map_angle), new_map)
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

    # Chooses sign of tangent by checking along ±vector
    # whether it goes toward border (white) which is penalized.
    def _choose_forward_sign(self, cx: float, cy: float, vx: float, vy: float) -> tuple[int, float, float]:
        from .finish_detection import choose_forward_sign
        return choose_forward_sign(self._surface, cx, cy, vx, vy, BORDER_COLOR[:3])

    # -------------------------------------------------------------------------
    # Debug rendering: draws detected finish line info on surface
    # -------------------------------------------------------------------------
    def draw_finish_debug(self, screen: pygame.Surface) -> None:
        """
        Draw bounding box, centroid, main direction and computed spawn point
        onto the given surface. Useful for debugging when the red line
        is not detected or spawn positions need verification.
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
        """Collect red pixels, compute BBox, centroid, principal direction, sign and proposed spawn.
        
        Returns:
            Dict with all relevant values for further evaluation/logging, or None on error.
        """
        try:
            xs, ys = self._collect_red_pixels_fast()
            if xs is None or ys is None:
                xs, ys = self._collect_red_pixels_slow()
        except Exception as e:
            log.debug("_detect_finish_info: Error collecting red pixels: %s", e)
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
        # Midpoint along tangent (better geometric center of the detected line)
        ts = [((x - cx_mean) * vx + (y - cy_mean) * vy) for x, y in zip(xs, ys)]
        tmin = min(ts)
        tmax = max(ts)
        tmid = 0.5 * (tmin + tmax)
        cx = cx_mean + tmid * vx
        cy = cy_mean + tmid * vy

        # Normal vector (for spawn direction)
        nx, ny = -vy, vx
        sign, s_pos, s_neg = self._choose_forward_sign(cx, cy, nx, ny)

        offset = max(20, int(1.5 * int(CAR_cover_size or 32)))
        spawn_x = int(cx + sign * nx * offset)
        spawn_y = int(cy + sign * ny * offset)
        # Vehicle heading = direction of normal (sign determines side)
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
        log.info("Manual spawn cleared; auto-detect re-enabled.")

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
