"""Assets Package - Resources for the simulation.

Contains:
- Map images (PNG): Tracks with walls (white), finish line (red)
- Vehicle sprites: Car graphics for rendering
- Fonts: TrueType fonts for HUD & UI text
- Configuration files: NEAT config, map metadata

Resources are loaded via relative paths:
    from crazycar.assets import get_asset_path
    map_path = get_asset_path('maps/track01.png')

Format Conventions:
- Maps: RGB(255,255,255) = wall, RGB(237,28,36) = finish line
- Sprites: Transparent background (alpha channel)
"""
