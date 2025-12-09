"""Vehicle Model - Physics, Sensors and Rendering.

This package implements the complete car model:

Core Modules:
- model: Car class (main interface)
- state: CarState (position, velocity, angle, etc.)
- constants: Physical parameters & configuration

Physics:
- kinematics: Steering geometry (Ackermann approximation)
- dynamics: Acceleration, deceleration, drag
- motion: Update step (position, rotation, boundaries)
- actuation: Power/Steer → Speed/Angle mapping

Collision:
- collision: Wall detection, finish line, rebound trigger
- rebound: Physical reflection & speed reduction
- geometry: Corner & wheel positions

Sensors:
- sensors: Radar casting (distance measurement)

Rendering:
- rendering: Sprite rotation, drawing, HUD
- serialization: State → Dict (logging, replay)

Utilities:
- units: Unit conversion (px ↔ m, etc.)
- timeutil: Frame timing & delays
"""
