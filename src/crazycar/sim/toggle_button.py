import pygame
# =============================================================================
# crazycar/sim/toggle_button.py  —  UI-Widget (Toggle mit 2–3 Zuständen)
# -----------------------------------------------------------------------------
# Aufgabe:
# - Einfacher, klickbarer Toggle-Button inklusive Zeichnen & Statusverwaltung.
# - Wird für Sensor-Enable und Collision-Model (Rebound/Stop/Remove) genutzt.
#
# Öffentliche API:
# - class ToggleButton:
#       rect: pygame.Rect
#       __init__(x: int, y: int, label_a: str, label_b: str, label_c: str = "")
#       draw(surface: pygame.Surface) -> None
#       handle_event(raw_event: pygame.event.Event, max_states: int = 2) -> None
#       get_status() -> int           # 0/1/(2) je nach max_states
#
# Hinweise:
# - Nutzt raw pygame-Events; deshalb liefert EventSource.last_raw() den Feed.
# =============================================================================


class ToggleButton:
    def __init__(self, x, y, text1, text2, text3):
        self.rect = pygame.Rect(x, y, 215, 45)
        font = pygame.font.Font(None, 25)
        self.text = [font.render(text1, True, (255, 255, 255)),
                     font.render(text2, True, (255, 255, 255)),
                     font.render(text3, True, (255, 255, 255))]

        self.color = [(20, 255, 0),
                      (255, 0, 0),
                      (0, 0, 255)]

        self.state = 0

    def draw(self, screen):
        pygame.draw.rect(screen, self.color[self.state], self.rect)
        screen.blit(self.text[self.state], (self.rect.x, self.rect.centery))

    def handle_event(self, event, zahl):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = (self.state + 1) % zahl

    def get_status(self):
        return self.state
