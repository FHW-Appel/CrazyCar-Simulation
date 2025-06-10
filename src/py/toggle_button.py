import pygame


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
