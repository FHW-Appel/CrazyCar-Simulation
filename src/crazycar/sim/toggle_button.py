"""UI Toggle-Button Widget.

Implements a clickable toggle button with 2-3 states for the
simulation UI (Sensor-Enable, Collision-Mode).

Class:
- ToggleButton: Pygame-based UI element

Features:
- Multi-State Toggle (2 or 3 states)
- Click-Handling via pygame.MOUSEBUTTONDOWN
- Visual feedback (color + text change)
- Status query via get_status()

Usage:
    btn = ToggleButton(x=100, y=50,
                       text1="Sensor ON",
                       text2="Sensor OFF",
                       text3="")
    btn.draw(screen)
    btn.handle_event(pygame_event, max_states=2)
    current = btn.get_status()  # 0 or 1

Constants:
- TOGGLE_WIDTH: 215px (button width)
- TOGGLE_HEIGHT: 45px (button height)
- TOGGLE_FONT_SIZE: 25pt (text size)
- Colors: Green (active), Red (inactive), Blue (third state)
"""
import pygame

# UI constants for toggle button
TOGGLE_WIDTH = 215  # pixels
TOGGLE_HEIGHT = 45  # pixels
TOGGLE_FONT_SIZE = 25  # points

# State colors (RGB)
COLOR_GREEN_ACTIVE = (20, 255, 0)      # State 0: Active/ON
COLOR_RED_INACTIVE = (255, 0, 0)       # State 1: Inactive/OFF
COLOR_BLUE_ALT = (0, 0, 255)           # State 2: Alternative (if 3 states)
WHITE_TEXT_COLOR = (255, 255, 255)     # Text color for all states


class ToggleButton:
    """Clickable toggle button with multiple states.
    
    Manages position, rendering and status of a UI button
    that toggles between 2-3 states.
    
    Attributes:
        rect (pygame.Rect): Button position and size
        text (List[pygame.Surface]): Rendered text labels for each state
        color (List[Tuple[int, int, int]]): RGB colors for each state
        state (int): Current state (0, 1, or 2)
    """
    
    def __init__(self, x, y, text1, text2, text3):
        """Initialize toggle button.
        
        Args:
            x (int): X-position (pixels, top left)
            y (int): Y-position (pixels, top left)
            text1 (str): Label for state 0
            text2 (str): Label for state 1
            text3 (str): Label for state 2 (optional, can be empty)
        """
        self.rect = pygame.Rect(x, y, TOGGLE_WIDTH, TOGGLE_HEIGHT)
        font = pygame.font.Font(None, TOGGLE_FONT_SIZE)
        self.text = [font.render(text1, True, WHITE_TEXT_COLOR),
                     font.render(text2, True, WHITE_TEXT_COLOR),
                     font.render(text3, True, WHITE_TEXT_COLOR)]

        self.color = [COLOR_GREEN_ACTIVE,
                      COLOR_RED_INACTIVE,
                      COLOR_BLUE_ALT]

        self.state = 0

    def draw(self, screen):
        """Draw button on surface.
        
        Args:
            screen (pygame.Surface): Target surface for rendering
        """
        pygame.draw.rect(screen, self.color[self.state], self.rect)
        screen.blit(self.text[self.state], (self.rect.x, self.rect.centery))

    def handle_event(self, event, zahl):
        """Process click events for state changes.
        
        Args:
            event (pygame.event.Event): Raw pygame event
            zahl (int): Maximum number of states (2 or 3)
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = (self.state + 1) % zahl

    def get_status(self):
        """Return current state.
        
        Returns:
            int: 0, 1, or 2 depending on active state
        """
        return self.state
