import pygame
import random

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLAYER_SIZE = 40
PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 20
GRAVITY = 0.8
JUMP_POWER = 15
MOVE_SPEED = 5
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)


class Player:
    def __init__(self, x, y):
        self.width = PLAYER_SIZE
        self.height = PLAYER_SIZE
        self.x = x
        self.y = y
        self.velocity_y = 0
        self.velocity_x = 0
        self.speed = MOVE_SPEED
        self.gravity = GRAVITY
        self.jump_charge = 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False
        self.is_charging = False
        self.last_space_state = False
        self.color = RED
        self.MAX_JUMP_CHARGE = 20
        self.bounce_velocity = 0

    def handle_jump(self, space_pressed):
        if self.on_ground:
            if space_pressed:
                if not self.is_charging:
                    self.is_charging = True
                    self.jump_charge = 0
                else:
                    self.jump_charge = min(self.jump_charge + 1, self.MAX_JUMP_CHARGE)
            elif self.is_charging:
                jump_power = -(JUMP_POWER + (self.jump_charge / 2))
                self.velocity_y = jump_power
                self.is_charging = False
                self.jump_charge = 0
                self.on_ground = False

        self.last_space_state = space_pressed

    def check_platform_collision(self, platforms):
        previous_rect = self.rect.copy()
        self.rect.x = self.x
        self.rect.y = self.y

        if self.velocity_y >= 0:
            self.on_ground = False
            for platform in platforms:
                if self.rect.colliderect(platform.rect):
                    if previous_rect.bottom <= platform.rect.top:
                        self.y = platform.rect.top - self.height
                        self.velocity_y = 0
                        self.on_ground = True
                        break

        self.rect.x = self.x
        self.rect.y = self.y

    def update(self):
        keys = pygame.key.get_pressed()
        self.velocity_x = 0

        # Handle bounce velocity separately from regular movement
        bounce_velocity = getattr(self, 'bounce_velocity', 0)

        # Only allow horizontal movement when in the air (for arrow keys)
        if not self.on_ground:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.velocity_x = -self.speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.velocity_x = self.speed

        # Apply gravity regardless of ground state
        self.velocity_y += self.gravity
        if self.velocity_y > 20:  # Terminal velocity
            self.velocity_y = 20

        # Apply both regular and bounce velocity
        self.x += self.velocity_x + bounce_velocity
        self.y += self.velocity_y

        # Screen bounds with bounce
        wall_bounce_strength = 20  # Increased bounce strength
        if self.x < 0:
            self.x = 0
            self.bounce_velocity = wall_bounce_strength
            self.velocity_x = 0  # Reset regular velocity
        elif self.x > WINDOW_WIDTH - self.width:
            self.x = WINDOW_WIDTH - self.width
            self.bounce_velocity = -wall_bounce_strength
            self.velocity_x = 0  # Reset regular velocity

        # Gradually reduce bounce velocity
        if getattr(self, 'bounce_velocity', 0) != 0:
            self.bounce_velocity *= 0.85  # Faster decay
            if abs(self.bounce_velocity) < 0.5:
                self.bounce_velocity = 0

        # Update color only when charging (otherwise keep previous color)
        if self.is_charging:
            self.color = BLUE
        else:
            self.color = RED

    def draw(self, screen, camera_y):
        adjusted_y = self.y - camera_y
        pygame.draw.rect(screen, self.color, (self.x, adjusted_y, self.width, self.height))


class Platform:
    def __init__(self, x, y, width=PLATFORM_WIDTH):
        self.rect = pygame.Rect(x, y, width, PLATFORM_HEIGHT)
        self.color = GREEN

    def draw(self, screen, camera_y):
        adjusted_y = self.rect.y - camera_y
        pygame.draw.rect(screen, self.color, (self.rect.x, adjusted_y, self.rect.width, self.rect.height))


class PlatformGenerator:
    def __init__(self):
        self.platforms = []
        self.min_platform_width = 60
        self.max_platform_width = 120
        self.platform_height = PLATFORM_HEIGHT
        self.vertical_gap_min = 80
        self.vertical_gap_max = 150
        self.max_horizontal_gap = 200
        self.generation_buffer = WINDOW_HEIGHT * 3
        self.highest_platform_y = 0

        # Generate initial platforms
        self.generate_initial_platforms()

    def generate_initial_platforms(self):
        # Create the floor as a regular platform
        floor = Platform(0, WINDOW_HEIGHT - 40, WINDOW_WIDTH)
        self.platforms = [floor]

        # Generate platforms starting from above the floor
        current_y = WINDOW_HEIGHT - 150
        while current_y > -self.generation_buffer:
            width = random.randint(self.min_platform_width, self.max_platform_width)
            x = random.randint(0, WINDOW_WIDTH - width)
            self.platforms.append(Platform(x, current_y, width))
            current_y -= random.randint(self.vertical_gap_min, self.vertical_gap_max)

        self.highest_platform_y = current_y

    def update(self, camera_y):
        # Remove ALL platforms that are too far below the camera
        view_bottom = camera_y + WINDOW_HEIGHT + 400
        self.platforms = [p for p in self.platforms if p.rect.y < view_bottom]

        # Generate new platforms above
        view_top = camera_y - self.generation_buffer

        # If there's too big of a gap between the highest platform and view_top, reset highest_platform_y
        if self.highest_platform_y - view_top > WINDOW_HEIGHT * 4:
            self.highest_platform_y = view_top + WINDOW_HEIGHT

        while self.highest_platform_y > view_top:
            width = random.randint(self.min_platform_width, self.max_platform_width)
            x = random.randint(0, WINDOW_WIDTH - width)
            new_platform = Platform(x, self.highest_platform_y, width)
            self.platforms.append(new_platform)
            self.highest_platform_y -= random.randint(self.vertical_gap_min, self.vertical_gap_max)

        # Safety check: ensure we always have some platforms
        if len(self.platforms) < 2:
            current_y = view_bottom - 200
            while current_y > view_top:
                width = random.randint(self.min_platform_width, self.max_platform_width)
                x = random.randint(0, WINDOW_WIDTH - width)
                self.platforms.append(Platform(x, current_y, width))
                current_y -= random.randint(self.vertical_gap_min, self.vertical_gap_max)
            self.highest_platform_y = current_y


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Platform Jumper")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.score = 0
        self.high_score = 0
        self.platform_generator = None
        self.player = None
        self.camera_y = 0
        self.reset_game()

    def reset_game(self):
        self.platform_generator = PlatformGenerator()
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 150)
        self.camera_y = 0
        self.game_over = False
        self.score = 0

    def calculate_score(self):
        return max(0, int(-self.camera_y / 10))

    def update(self):
        keys = pygame.key.get_pressed()

        if self.game_over:
            if keys[pygame.K_SPACE]:
                self.reset_game()
            return

        # Update player
        self.player.handle_jump(keys[pygame.K_SPACE])
        self.player.update()
        self.player.check_platform_collision(self.platform_generator.platforms)

        # Camera following player - move camera up when player goes above half screen
        if self.player.y < WINDOW_HEIGHT / 2:
            target_camera_y = -(WINDOW_HEIGHT / 2 - self.player.y)
            self.camera_y = target_camera_y

        # Update platforms and score
        self.platform_generator.update(self.camera_y)
        # Remove platforms that are too far below the camera view, including the starting platform
        self.platform_generator.platforms = [p for p in self.platform_generator.platforms
                                             if p.rect.y < self.camera_y + WINDOW_HEIGHT + 400]

        self.score = self.calculate_score()
        self.high_score = max(self.score, self.high_score)

        # Game over when player falls below visible area
        if self.player.y > self.camera_y + WINDOW_HEIGHT:
            self.game_over = True

    def draw(self):
        self.screen.fill(BLACK)

        # Draw platforms
        for platform in self.platform_generator.platforms:
            platform.draw(self.screen, self.camera_y)

        # Draw player
        self.player.draw(self.screen, self.camera_y)

        # Draw score
        font = pygame.font.Font(None, 36)
        score_text = font.render(f'Score: {self.score}', True, WHITE)
        high_score_text = font.render(f'High Score: {self.high_score}', True, WHITE)
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(high_score_text, (10, 50))

        if self.game_over:
            game_over_text = font.render('Game Over! Press SPACE to restart', True, WHITE)
            text_rect = game_over_text.get_rect(center=(WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2))
            self.screen.blit(game_over_text, text_rect)

        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.update()
            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    game = Game()
    game.run()
    pygame.quit()
