"""Simulation Package - Main Loop, Event Handling, Rendering.

Core Components:
- loop: Main game loop (Event → Update → Draw)
- simulation: High-level simulation entry point
- state: SimConfig, SimRuntime, SimEvent (central data structures)

Event System:
- event_source: pygame.event → SimEvent normalization
- modes: ModeManager (Menu, Play, Pause, Dialog)

Map & Spawn:
- map_service: MapService (map image loader, color lookup)
- spawn_utils: Vehicle spawn at start position
- finish_detection: Finish line detection via PCA

Rendering:
- screen_service: Pygame display setup & management
- snapshot_service: Screenshot creation

UI:
- toggle_button: Clickable toggle buttons (sensor, collision mode)
"""
