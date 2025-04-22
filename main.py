import pygame
import random
import os

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 80
PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 20
GRAVITY = 0.8
JUMP_POWER = 25
MOVE_SPEED = 3.5
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)


class Player:
    def __init__(self, x, y):
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.x = x
        self.y = y
        # Load sprites
        self.sprites = {
            'standing': pygame.image.load(os.path.join('assets', 'player.png')),
            'jumping': pygame.image.load(os.path.join('assets', 'player_jump.png'))
        }
        # Scale all sprites to match player dimensions
        for key in self.sprites:
            self.sprites[key] = pygame.transform.scale(self.sprites[key], (self.width, self.height))
        self.image = self.sprites['standing']  # Default sprite
        # Add a direction flag
        self.facing_right = True  # True for right, False for left
        self.velocity_y = 0
        self.velocity_x = 0
        self.speed = MOVE_SPEED
        self.gravity = GRAVITY
        self.jump_charge = 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.on_ground = False
        self.is_charging = False
        self.last_space_state = False
        self.WALL_BOUNCE_STRENGTH = 20
        self.BOUNCE_DECAY = 0.85
        self.MAX_JUMP_CHARGE = 20
        self.bounce_velocity = 0

    def handle_jump(self, space_pressed):
        # Consider adding variable jump heights based on how long space is pressed
        if self.on_ground:
            if space_pressed:
                self.jump_charge = min(self.jump_charge + 0.5, self.MAX_JUMP_CHARGE)
            elif self.last_space_state and not space_pressed:
                # Jump power could be more dynamic
                self.velocity_y = -JUMP_POWER * (self.jump_charge / self.MAX_JUMP_CHARGE)
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

        if keys[pygame.K_LEFT]:
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            self.facing_right = True
        if not self.on_ground:
            self.image = self.sprites['jumping']
        else:
            self.image = self.sprites['standing']
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

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
        wall_bounce_strength = min(abs(self.velocity_x) + self.WALL_BOUNCE_STRENGTH, self.WALL_BOUNCE_STRENGTH * 1.5)
        # Wall collision with dynamic bounce
        if self.x < 0:
            self.x = 0
            self.bounce_velocity = wall_bounce_strength
            self.velocity_x = 0
        elif self.x > WINDOW_WIDTH - self.width:
            self.x = WINDOW_WIDTH - self.width
            self.bounce_velocity = -wall_bounce_strength
            self.velocity_x = 0

        # Gradually reduce bounce velocity
        if getattr(self, 'bounce_velocity', 0) != 0:
            self.bounce_velocity *= 0.85  # Faster decay
            if abs(self.bounce_velocity) < 0.5:
                self.bounce_velocity = 0

    def get_charge_color(self):
        # Convert charge level to a color from green to red
        charge_ratio = self.jump_charge / self.MAX_JUMP_CHARGE
        # RGB interpolation from green (0, 255, 0) to red (255, 0, 0)
        red = int(255 * charge_ratio)
        green = int(255 * (1 - charge_ratio))
        return red, green, 0

    def draw(self, screen, camera_y):
        adjusted_y = self.rect.y - camera_y
        screen.blit(self.image, (self.rect.x, adjusted_y))

        # Draw charge indicator if charging
        if self.last_space_state:
            # Calculate indicator dimensions
            indicator_width = self.width * (self.jump_charge / self.MAX_JUMP_CHARGE)
            indicator_height = 5
            indicator_y = adjusted_y + self.height + 5  # Position it 5 pixels below the player

            # Draw the charge bar
            pygame.draw.rect(screen, self.get_charge_color(),
                             (self.rect.x, indicator_y, indicator_width, indicator_height))
            # Draw the empty bar outline
            pygame.draw.rect(screen, BLACK,
                             (self.rect.x, indicator_y, self.width, indicator_height), 1)


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
        self.max_horizontal_gap = 300  # Add this new parameter to control horizontal gaps
        self.generation_buffer = WINDOW_HEIGHT * 3
        self.highest_platform_y = 0
        self.last_x = WINDOW_WIDTH // 2  # Add this to track the last platform's position
        self.generate_initial_platforms()

    def get_next_platform_x(self, width):
        # Helper method to calculate next platform x position
        min_x = max(0, self.last_x - self.max_horizontal_gap)
        max_x = min(WINDOW_WIDTH - width, self.last_x + self.max_horizontal_gap)

        if min_x > WINDOW_WIDTH - width:
            min_x = 0
        if max_x < 0:
            max_x = WINDOW_WIDTH - width

        new_x = random.randint(min_x, max_x)
        self.last_x = new_x
        return new_x

    def generate_initial_platforms(self):
        # Create the floor as a regular platform
        floor = Platform(0, WINDOW_HEIGHT - 40, WINDOW_WIDTH)
        self.platforms = [floor]
        self.last_x = WINDOW_WIDTH // 2

        # Generate platforms starting from above the floor
        current_y = WINDOW_HEIGHT - 150
        while current_y > -self.generation_buffer:
            width = random.randint(self.min_platform_width, self.max_platform_width)
            x = self.get_next_platform_x(width)  # Use the new method instead of completely random x
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

        if not self.game_over:
            # Get the lowest platform's y position
            lowest_platform = max(
                p.rect.y for p in self.platform_generator.platforms) if self.platform_generator.platforms else 0

            # If player falls more than 2 screen heights below the lowest platform, game over
            if self.player.rect.top > lowest_platform + WINDOW_HEIGHT * 2:
                self.game_over = True
                return

        # Game over when player falls below visible area
        if self.player.rect.top > self.camera_y + WINDOW_HEIGHT * 1.5:  # 1.5 screens below camera
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
