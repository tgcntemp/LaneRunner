import logging
import random
import carla
import pygame
import math

# Local imports
from src.core.colors import COLOR_AQUAMARINE, COLOR_DUKEBLUE
from src.data.coin import Coin
from src.data.game_state import GameState
from src.data.avatar import Avatar
from src.data.sounds import Sounds
from src.data.sound_mixer import SoundMixer
from src.core.constants import (
    BUTTON_BACKGROUND_PATH,
    COIN_SPACING, 
    COIN_NUMBER, 
    COIN_COLLISION_RADIUS, 
    COIN_REMOVE_THRESHOLD,
    COIN_COUNTER_ICON_PATH,
    CORNER_BOTTOM_RIGHT_PATH,
    CORNER_TOP_LEFT_PATH,
    FONT_BOLD_PATH,
    FONT_REGULAR_MONTSERRAT_PATH,
    FONT_REGULAR_PATH,
    MENU_BACKGROUND_PATH,
    MENU_HEADER_BACKGROUND_PATH,
    TAKE_OVER_COUNTDOWN,
    STARTING_COUNTDOWN,
    AVATAR_COLLISION_RADIUS,
    HEART_FILLED_PATH,
    HEART_EMPTY_PATH
    )

class GameManager:
    def __init__(self):
        self.game_state = GameState.MANUAL_DRIVING  # Initial game state
        self.has_game_started = False  # Flag to track if the game has started
        self.has_gamified_active = False

        # Player information
        self.player_score = 0

        # Avatar
        self.avatar = None

        # Coins
        self.coins = {}
        self.last_coin_wp = None  # Last coin waypoint for spawning new coins

        # Takeover request
        self.takeover_countdown = 0
        self.takeover_timer = 0

        # Starting time
        self.starting_countdown = 0
        self.starting_timer = 0

        # Image assets (initialized as None, loaded in start)
        self._img_border_topleft = None
        self._img_border_bottomright = None
        self._img_coin = None
        self._img_menu_bg = None
        self._img_menu_header_bg = None
        self._img_button_bg = None
        self._img_heart_filled = None
        self._img_heart_empty = None

    def start(self, hero_wp):
        # Load images if not already loaded
        if self._img_border_topleft is None:
            self._img_border_topleft = pygame.image.load(CORNER_TOP_LEFT_PATH).convert_alpha()
        if self._img_border_bottomright is None:
            self._img_border_bottomright = pygame.image.load(CORNER_BOTTOM_RIGHT_PATH).convert_alpha()
        if self._img_coin is None:
            self._img_coin = pygame.image.load(COIN_COUNTER_ICON_PATH).convert_alpha()
        if self._img_menu_bg is None:
            self._img_menu_bg = pygame.image.load(MENU_BACKGROUND_PATH).convert_alpha()
        if self._img_menu_header_bg is None:
            self._img_menu_header_bg = pygame.image.load(MENU_HEADER_BACKGROUND_PATH).convert_alpha()
        if self._img_button_bg is None:
            self._img_button_bg = pygame.image.load(BUTTON_BACKGROUND_PATH).convert_alpha()
        if self._img_heart_filled is None:
            self._img_heart_filled = pygame.image.load(HEART_FILLED_PATH).convert_alpha()
        if self._img_heart_empty is None:
            self._img_heart_empty = pygame.image.load(HEART_EMPTY_PATH).convert_alpha()

        self.avatar = Avatar()
        self.avatar.start(hero_wp)
        self.spawn_coins(hero_wp)

    def update(self, vehicles):
        self.check_spawn_need()
        self.check_avatar_vehicle_collisions(vehicles)
        self.check_coin_collisions(vehicles)

    def start_game(self):
        if self.game_state != GameState.MANUAL_DRIVING and self.game_state != GameState.GAME_OVER and self.game_state != GameState.PAUSED and self.game_state != GameState.END_GAME:
            logging.warning("Cannot start game. Current state: %s", self.game_state)
            return

        self.starting_countdown = STARTING_COUNTDOWN
        self.starting_timer = 0
        self.game_state = GameState.STARTING

    def update_starting(self, delta_time, hero_wp):
        """
        Update the game state from STARTING to IN_GAME after a short delay.
        """
        if self.game_state == GameState.STARTING:
            self.starting_timer += delta_time

            if self.starting_timer >= 1.0:
                self.starting_countdown -= 1
                self.starting_timer = 0
                logging.debug(f"Starting countdown: {self.starting_countdown}")
            if self.starting_countdown <= 0:
                if self.has_game_started:
                    self.resume_game()
                else:
                    self.new_game(hero_wp)

                self.starting_countdown = 0
                self.starting_timer = 0

                logging.debug("Game started.")
            
        else:
            logging.warning("Cannot update game state. Current state: %s", self.game_state)

    def new_game(self, hero_wp):
        """
        Start a new game, resetting the game state and player score.
        """
        self.game_state = GameState.STARTING
        self.player_score = 0
        self.avatar = Avatar()
        self.avatar.start(hero_wp)
        self.spawn_coins(hero_wp)
        self.has_game_started = True
        logging.debug("New game started.")

    def toggle_game(self):
        if self.game_state == GameState.IN_GAME:
            self.pause_game()
        elif self.game_state == GameState.PAUSED:
            self.start_game()
        else:
            logging.warning("Cannot toggle game state. Current state: %s", self.game_state)

    def pause_game(self):
        if self.game_state == GameState.IN_GAME:
            self.game_state = GameState.PAUSED
            logging.debug("Game paused.")
        else:
            logging.warning("Cannot pause the game. Current state: %s", self.game_state)

    def resume_game(self):
        if self.game_state == GameState.STARTING:
            self.game_state = GameState.IN_GAME
            self.avatar.invulnerable = True
            logging.debug("Game resumed.")
        else:
            logging.warning("Cannot resume the game. Current state: %s", self.game_state)
    
    def end_game(self):
        self.game_state = GameState.END_GAME
        logging.debug("Game ended.")

    def request_takeover(self):
        if self.game_state in [
            GameState.STARTING,
            GameState.IN_GAME,
            GameState.PAUSED,
            GameState.GAME_OVER,
            GameState.END_GAME
        ]:
            SoundMixer.instance().play(Sounds.TAKE_OVER_REQUIRED)

            self.game_state = GameState.TAKEOVER_REQUESTING
            self.takeover_countdown = TAKE_OVER_COUNTDOWN
            self.takeover_timer = 0


            logging.debug("Takeover requested.")
        else:
            logging.warning("Cannot request takeover. Current state: %s", self.game_state)
    
    def update_takeover(self, delta_time):
        if self.game_state == GameState.TAKEOVER_REQUESTING:
            self.takeover_timer += delta_time
            
            if self.takeover_timer >= 1.0:
                self.takeover_countdown -= 1
                self.takeover_timer = 0
                logging.debug(f"Takeover countdown: {self.takeover_countdown}")
            if self.takeover_countdown <= 0:
                for _ in range(3):
                    SoundMixer.instance().play(Sounds.TOR_ALERT)
                    
                self.game_state = GameState.MANUAL_DRIVING
                self.takeover_countdown = 0
                self.takeover_timer = 0


    def game_over(self):
        if self.game_state in [GameState.IN_GAME, GameState.PAUSED]:
            self.game_state = GameState.GAME_OVER
            SoundMixer.instance().play(Sounds.GAME_OVER)
            logging.debug("Game over.")
        else:
            logging.warning("Cannot set game over. Current state: %s", self.game_state)

    def restart_game(self):
        if self.game_state in [GameState.IN_GAME, GameState.PAUSED, GameState.GAME_OVER, GameState.END_GAME]:
            self.has_game_started = False
            self.coins.clear()
            self.start_game()
            logging.debug("Game restarted.")
        else:
            logging.warning("Cannot restart the game. Current state: %s", self.game_state)

    def get_state(self):
        return self.game_state
    
    def spawn_coins(self, hero_wp, num_coins=COIN_NUMBER, spacing=COIN_SPACING):
        # Find all drivable lane_ids and their waypoints at the hero's location
        lane_wps = {}
        for offset in [-2, -1, 0, 1, 2]:  # Adjust range as needed for your map
            try:
                wp = hero_wp
                for _ in range(abs(offset)):
                    wp = wp.get_left_lane() if offset < 0 else wp.get_right_lane()
                if wp and wp.lane_type == carla.LaneType.Driving:
                    lane_wps[wp.lane_id] = wp
            except Exception:
                continue
    
        if not lane_wps:
            lane_wps = {hero_wp.lane_id: hero_wp}  # fallback
    
        lane_ids = list(lane_wps.keys())
        base_wps = list(lane_wps.values())
    
        # Start from the hero's waypoint and move forward by spacing each time
        wp = hero_wp
        placed = 0
        while placed < num_coins:
            # At each row, randomly pick a lane
            lane_idx = random.randint(0, len(lane_ids) - 1)
            lane_id = lane_ids[lane_idx]
            # For this row, get the waypoint for the chosen lane
            row_wps = []
            for base_wp in base_wps:
                next_wps = base_wp.next(spacing * (placed + 1))
                for candidate_wp in next_wps:
                    if candidate_wp.lane_id == lane_id and candidate_wp.lane_type == carla.LaneType.Driving:
                        row_wps.append(candidate_wp)
                        break
            if row_wps:
                coin_wp = row_wps[0]
                coin = Coin(coin_wp)
                self.coins[coin.id] = coin
                placed += 1

                self.last_coin_wp = coin_wp
            else:
                # If no waypoint found, break to avoid infinite loop
                break

        logging.debug("Coins spawned. Total coins: %s", len(self.coins))

    def check_spawn_need(self):
        if not self.avatar or not self.avatar.current_wp:
            return
        
        if len(self.coins) == 0:
            self.spawn_coins(self.avatar.current_wp)
    
        # TODO: Handle more solid fail-safe cases
        # Fail-safe: If avatar is on a different lane type, respawn coins at avatar's location
        if self.last_coin_wp:
            if self.avatar.current_wp.lane_type != self.last_coin_wp.lane_type and self.avatar.current_wp.road_id != self.last_coin_wp.road_id:
                logging.warning(
                    "Fail-safe: Avatar is on a different lane type or road. "
                    "Last coin lane type: %s, Avatar lane type: %s",
                    self.last_coin_wp.lane_type, self.avatar.current_wp.lane_type
                )
                self.spawn_coins(self.avatar.current_wp)
                logging.debug(
                    "Fail-safe: Spawned new coins at avatar's new lane type: %s",
                    self.avatar.current_wp.lane_type
                )
                return
    
        # Normal: Spawn coins when avatar is near the last coin
        if self.last_coin_wp:
            distance = self.avatar.current_wp.transform.location.distance(self.last_coin_wp.transform.location)
            if distance < COIN_SPACING:
                self.spawn_coins(self.last_coin_wp)
                logging.debug(
                    "Spawned new coins at last coin's location: %s",
                    self.last_coin_wp.transform.location
                )

            if distance > 120:
                self.spawn_coins(self.avatar.current_wp)
                logging.debug(
                    "Spawned new coins at last coin's location: %s",
                    self.avatar.current_wp.transform.location
                )

    def _select_continuous_path(self, wps, prefer_lane_id=None):
        """
        Pick a waypoint from multiple options, preferring one that matches the current lane.
        Used in junctions where waypoint.next(distance) returns multiple options.
        Returns None if no suitable path is found.
        """
        if not wps:
            return None

        # Prefer the path that matches previous lane
        for wp in wps:
            if prefer_lane_id is not None and wp.lane_id == prefer_lane_id:
                return wp

        # Fallback: choose the first drivable lane
        for wp in wps:
            if wp.lane_type == carla.LaneType.Driving:
                return wp

        # No suitable path found
        return None
    
    def draw_coins(self, surface, world_to_pixel, world_to_pixel_width):
        """
        Draw all visible coins on the given surface.
        """
        for coin in self.coins.values():
            coin.draw(surface, world_to_pixel, world_to_pixel_width)

    def check_coin_collisions(self, vehicles):
        """
        Check for collisions between coins and avatar or vehicles.
        If avatar collides with a coin, collect and remove it.
        If a vehicle collides with a coin, hide it.
        If not colliding, show it again.
        Also remove coins that are far behind the avatar.
        """
        avatar_location = self.avatar.current_wp.transform.location if self.avatar and self.avatar.current_wp else None
        coins_to_remove = []

        for coin in list(self.coins.values()):
            coin_location = coin.wp.transform.location

            # Remove coins that are left behind and not collected
            if avatar_location:
                # Vector from avatar to coin
                dx = coin_location.x - avatar_location.x
                dy = coin_location.y - avatar_location.y

                # Avatar's forward vector (assuming CARLA uses yaw in degrees)
                yaw = self.avatar.current_wp.transform.rotation.yaw
                forward_x = math.cos(math.radians(yaw))
                forward_y = math.sin(math.radians(yaw))

                # Dot product: negative means behind
                dot = dx * forward_x + dy * forward_y

                distance = math.sqrt(dx**2 + dy**2)
                if dot < 0 and distance > COIN_REMOVE_THRESHOLD:
                    coins_to_remove.append(coin.id)
                    continue

            # Check collision with avatar
            if avatar_location and coin_location.distance(avatar_location) < COIN_COLLISION_RADIUS:
                coin.collect()
                coins_to_remove.append(coin.id)
                self.player_score += 1
                logging.debug(f"Coin collected by avatar at {coin_location}")
                logging.debug(f"Player score: {self.player_score}")
                continue

            # Check collision with vehicles
            hidden = False
            for vehicle in vehicles:
                vehicle_location = vehicle.get_location()
                if coin_location.distance(vehicle_location) < COIN_COLLISION_RADIUS:
                    coin.hide()
                    hidden = True
                    break
            if not hidden:
                coin.show()

        # Remove collected or obsolete coins
        for coin_id in coins_to_remove:
            del self.coins[coin_id]
    
    def check_avatar_vehicle_collisions(self, vehicles):
        """
        Check for collisions between the avatar and vehicles.
        If a collision occurs, handle avatar death and game over.
        """
        if not self.avatar or not self.avatar.current_wp:
            return

        avatar_location = self.avatar.current_wp.transform.location

        for vehicle in vehicles:
            vehicle_location = vehicle.get_location()
            if avatar_location.distance(vehicle_location) < AVATAR_COLLISION_RADIUS:
                killed = self.avatar.kill()
                if killed:
                    self.game_state = GameState.GAME_OVER
                    SoundMixer.instance().play(Sounds.GAME_OVER)
                    logging.debug("Game over: Avatar collided with vehicle.")
                break

    def draw_coin_counter(self, surface):
        # Use cached images
        border_topleft = self._img_border_topleft
        border_bottomright = self._img_border_bottomright
        coin_img = self._img_coin

        # --- Set sizes and positions ---
        counter_width, counter_height = 220, 120  # Adjust as needed
        counter_x, counter_y = 0, 0  # Top-left corner

        # Draw a transparent background for the counter (optional)
        counter_bg = pygame.Surface((counter_width, counter_height), pygame.SRCALPHA)
        counter_bg.fill((0, 0, 0, 0))  # Semi-transparent black

        # Blit border images
        counter_bg.blit(border_topleft, (0, 0))
        counter_bg.blit(border_bottomright, (counter_width - border_bottomright.get_width(), counter_height - border_bottomright.get_height()))

        # Blit coin image (center left)
        coin_size = 60
        coin_img = pygame.transform.scale(coin_img, (coin_size, coin_size))
        coin_y = (counter_height - coin_size) // 2
        counter_bg.blit(coin_img, (32, coin_y))

        # Render coin text (center right)
        coin_text = f"{self.player_score}"
        font = pygame.font.Font(FONT_BOLD_PATH or None, 50)
        text_surface = font.render(coin_text, True, COLOR_DUKEBLUE)
        text_x = coin_size + 40
        text_y = (counter_height - text_surface.get_height()) // 2
        counter_bg.blit(text_surface, (text_x, text_y))

        # Blit the whole counter to the main surface
        surface.blit(counter_bg, (counter_x, counter_y))

    def draw_live_counter(self, surface):
        """
        Draws a live (heart) counter at the top-left, showing filled and empty hearts
        based on avatar's current_life and total lives.
        """
        border_topleft = self._img_border_topleft
        border_bottomright = self._img_border_bottomright
        heart_filled = self._img_heart_filled
        heart_empty = self._img_heart_empty

        counter_width, counter_height = 220, 120
        counter_x, counter_y = 0, 130  # Below the coin counter

        counter_bg = pygame.Surface((counter_width, counter_height), pygame.SRCALPHA)
        counter_bg.fill((0, 0, 0, 0))

        # Blit border images
        counter_bg.blit(border_topleft, (0, 0))
        counter_bg.blit(
            border_bottomright,
            (counter_width - border_bottomright.get_width(), counter_height - border_bottomright.get_height())
        )

        # Get lives info from avatar
        lives = self.avatar.current_life if self.avatar else 0
        max_lives = self.avatar.lives if self.avatar else 3

        # Heart icon settings
        heart_size = 40
        spacing = 8
        total_width = max_lives * heart_size + (max_lives - 1) * spacing
        start_x = (counter_width - total_width) // 2
        y = (counter_height - heart_size) // 2

        # Draw hearts
        for i in range(max_lives):
            img = heart_filled if i < lives else heart_empty
            heart_img = pygame.transform.scale(img, (heart_size, heart_size))
            counter_bg.blit(heart_img, (start_x + i * (heart_size + spacing), y))

        # Blit the counter to the main surface
        surface.blit(counter_bg, (counter_x, counter_y))

    def draw_takeover_request(self, surface):
        if self.game_state != GameState.TAKEOVER_REQUESTING:
            return

        # --- Pill-shaped label ---
        pill_width, pill_height = 340, 60
        pill_x, pill_y = (surface.get_width() - pill_width) // 2, 40
        pill_rect = pygame.Rect(pill_x, pill_y, pill_width, pill_height)
        border_color = (220, 30, 30)
        bg_color = (239, 41, 41, 65)
        pygame.draw.rect(surface, bg_color, pill_rect, border_radius=30)
        pygame.draw.rect(surface, border_color, pill_rect, width=4, border_radius=30)

        font = pygame.font.Font(FONT_REGULAR_MONTSERRAT_PATH or None, 24)
        label = "Take Over Request"
        text_surface = font.render(label, True, border_color)
        text_rect = text_surface.get_rect(center=pill_rect.center)
        surface.blit(text_surface, text_rect)

        # --- Countdown Circle ---
        circle_radius = 60
        circle_center = (surface.get_width() // 2, pill_y + pill_height + 80)
        pygame.draw.circle(surface, (255, 255, 255, 0), circle_center, circle_radius)
        circle_border_color = (220, 30, 30, 50)
        pygame.draw.circle(surface, circle_border_color, circle_center, circle_radius, width=6)

        total = TAKE_OVER_COUNTDOWN
        remaining = max(0, self.takeover_countdown)
        elapsed = total - remaining + self.takeover_timer
        progress = min(1.0, elapsed / total)
        end_angle = -90 + 360 * progress

        rect = pygame.Rect(0, 0, circle_radius * 2, circle_radius * 2)
        rect.center = circle_center
        if progress > 0:
            pygame.draw.arc(
                surface,
                border_color,
                rect,
                math.radians(90),
                math.radians(-end_angle),
                10
            )

        font2 = pygame.font.Font(FONT_REGULAR_MONTSERRAT_PATH or None, 60)
        num_surface = font2.render(str(remaining), True, border_color)
        num_rect = num_surface.get_rect(center=circle_center)
        surface.blit(num_surface, num_rect)

    def draw_starting(self, surface):
        if self.game_state != GameState.STARTING:
            return

        # --- Pill-shaped label ---
        pill_width, pill_height = 340, 60
        pill_x, pill_y = (surface.get_width() - pill_width) // 2, 40
        pill_rect = pygame.Rect(pill_x, pill_y, pill_width, pill_height)
        border_color = COLOR_DUKEBLUE
        bg_color = (53, 6, 160, 65)
        pygame.draw.rect(surface, bg_color, pill_rect, border_radius=30)
        pygame.draw.rect(surface, border_color, pill_rect, width=4, border_radius=30)

        font = pygame.font.Font(FONT_REGULAR_MONTSERRAT_PATH or None, 24)
        label = "Starting Game..."
        text_surface = font.render(label, True, border_color)
        text_rect = text_surface.get_rect(center=pill_rect.center)
        surface.blit(text_surface, text_rect)

        # --- Countdown Circle ---
        circle_radius = 60
        circle_center = (surface.get_width() // 2, pill_y + pill_height + 80)
        pygame.draw.circle(surface, (255, 255, 255, 0), circle_center, circle_radius)
        circle_border_color = COLOR_DUKEBLUE
        pygame.draw.circle(surface, circle_border_color, circle_center, circle_radius, width=6)

        total = STARTING_COUNTDOWN
        remaining = max(0, self.starting_countdown)
        elapsed = total - remaining + self.starting_timer
        progress = min(1.0, elapsed / total)
        end_angle = -90 + 360 * progress

        rect = pygame.Rect(0, 0, circle_radius * 2, circle_radius * 2)
        rect.center = circle_center
        if progress > 0:
            pygame.draw.arc(
                surface,
                border_color,
                rect,
                math.radians(90),
                math.radians(-end_angle),
                10
            )

        font2 = pygame.font.Font(FONT_REGULAR_MONTSERRAT_PATH or None, 60)
        num_surface = font2.render(str(remaining), True, border_color)
        num_rect = num_surface.get_rect(center=circle_center)
        surface.blit(num_surface, num_rect)

    def draw_game_over_menu(self, surface):
        if self.game_state != GameState.GAME_OVER:
            return

        # Use cached images
        bg_img = self._img_menu_bg
        corner_topleft = self._img_border_topleft
        corner_bottomright = self._img_border_bottomright
        header_bg = self._img_menu_header_bg
        coin_img = self._img_coin
        button_bg = self._img_button_bg

        # --- Center menu background on surface ---
        bg_rect = bg_img.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
        surface.blit(bg_img, bg_rect.topleft)

        # Blit corners relative to menu background
        corner_padding = 8
        surface.blit(corner_topleft, (bg_rect.left, bg_rect.top + corner_padding))
        surface.blit(
            corner_bottomright,
            (bg_rect.right - corner_bottomright.get_width(), bg_rect.bottom - corner_bottomright.get_height() - corner_padding)
        )

        # --- Header ---
        header_width, header_height = 400, 90
        header_x = bg_rect.left + (bg_rect.width - header_width) // 2
        header_y = bg_rect.top + 60
        header_bg = pygame.transform.scale(header_bg, (header_width, header_height))
        surface.blit(header_bg, (header_x, header_y))

        font_header = pygame.font.Font(FONT_REGULAR_PATH or None, 48)
        header_text = font_header.render("Game Over", True, COLOR_AQUAMARINE)
        header_rect = header_text.get_rect(center=(bg_rect.centerx, header_y + header_height // 2))
        surface.blit(header_text, header_rect)

        # --- Centered content (relative to menu background) ---
        center_x = bg_rect.centerx
        content_y = header_y + header_height + 40

        # Coin image
        coin_size = 90
        coin_img = pygame.transform.scale(coin_img, (coin_size, coin_size))
        coin_rect = coin_img.get_rect(center=(center_x, content_y + coin_size // 2))
        surface.blit(coin_img, coin_rect)

        # Total score
        font_score = pygame.font.Font(FONT_REGULAR_PATH or None, 48)
        score_text = font_score.render(str(self.player_score), True, COLOR_DUKEBLUE)
        score_rect = score_text.get_rect(center=(center_x, coin_rect.bottom + 40))
        surface.blit(score_text, score_rect)

        # "Your Coins" text
        font_label = pygame.font.Font(FONT_REGULAR_PATH or None, 32)
        label_text = font_label.render("Your Coins", True, COLOR_DUKEBLUE)
        label_rect = label_text.get_rect(center=(center_x, score_rect.bottom + 32))
        surface.blit(label_text, label_rect)

        # --- Buttons ---
        button_width, button_height = 180, 70
        buttons_y = label_rect.bottom + 50

        # Restart Button
        restart_x = center_x - button_width // 2
        restart_rect = pygame.Rect(restart_x, buttons_y, button_width, button_height)
        button_bg_scaled = pygame.transform.scale(button_bg, (button_width, button_height))
        surface.blit(button_bg_scaled, restart_rect.topleft)
        font_btn = pygame.font.Font(FONT_REGULAR_PATH or None, 28)
        restart_text = font_btn.render("New Game (N)", True, COLOR_AQUAMARINE)
        restart_text_rect = restart_text.get_rect(center=restart_rect.center)
        surface.blit(restart_text, restart_text_rect)

        # Store button rects for click detection
        self._game_over_buttons = {"restart": restart_rect}

    def draw_victory_menu(self, surface):
        if self.game_state != GameState.END_GAME:
            return

        # Use cached images
        bg_img = self._img_menu_bg
        corner_topleft = self._img_border_topleft
        corner_bottomright = self._img_border_bottomright
        header_bg = self._img_menu_header_bg
        coin_img = self._img_coin
        button_bg = self._img_button_bg

        # --- Center menu background on surface ---
        bg_rect = bg_img.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
        surface.blit(bg_img, bg_rect.topleft)

        # Blit corners relative to menu background
        corner_padding = 8
        surface.blit(corner_topleft, (bg_rect.left, bg_rect.top + corner_padding))
        surface.blit(
            corner_bottomright,
            (bg_rect.right - corner_bottomright.get_width(), bg_rect.bottom - corner_bottomright.get_height() - corner_padding)
        )

        # --- Header ---
        header_width, header_height = 400, 90
        header_x = bg_rect.left + (bg_rect.width - header_width) // 2
        header_y = bg_rect.top + 60
        header_bg = pygame.transform.scale(header_bg, (header_width, header_height))
        surface.blit(header_bg, (header_x, header_y))

        font_header = pygame.font.Font(FONT_REGULAR_PATH or None, 48)
        header_text = font_header.render("You Win!", True, COLOR_AQUAMARINE)
        header_rect = header_text.get_rect(center=(bg_rect.centerx, header_y + header_height // 2))
        surface.blit(header_text, header_rect)

        # --- Centered content (relative to menu background) ---
        center_x = bg_rect.centerx
        content_y = header_y + header_height + 40

        # Coin image
        coin_size = 90
        coin_img = pygame.transform.scale(coin_img, (coin_size, coin_size))
        coin_rect = coin_img.get_rect(center=(center_x, content_y + coin_size // 2))
        surface.blit(coin_img, coin_rect)

        # Total score
        font_score = pygame.font.Font(FONT_REGULAR_PATH or None, 48)
        score_text = font_score.render(str(self.player_score), True, COLOR_DUKEBLUE)
        score_rect = score_text.get_rect(center=(center_x, coin_rect.bottom + 40))
        surface.blit(score_text, score_rect)

        # "Your Coins" text
        font_label = pygame.font.Font(FONT_REGULAR_PATH or None, 32)
        label_text = font_label.render("Your Coins", True, COLOR_DUKEBLUE)
        label_rect = label_text.get_rect(center=(center_x, score_rect.bottom + 32))
        surface.blit(label_text, label_rect)

        # --- Buttons ---
        button_width, button_height = 180, 70
        buttons_y = label_rect.bottom + 50

        # Center the single button
        quit_x = center_x - button_width // 2
        quit_rect = pygame.Rect(quit_x, buttons_y, button_width, button_height)
        button_bg_scaled = pygame.transform.scale(button_bg, (button_width, button_height))
        surface.blit(button_bg_scaled, quit_rect.topleft)
        font_btn = pygame.font.Font(FONT_REGULAR_PATH or None, 28)
        quit_text = font_btn.render("Quit", True, COLOR_AQUAMARINE)
        quit_text_rect = quit_text.get_rect(center=quit_rect.center)
        surface.blit(quit_text, quit_text_rect)

        # Store button rects for click detection
        self._game_over_buttons = {"quit": quit_rect}


    def draw_pause_menu(self, surface):
        if self.game_state != GameState.PAUSED:
            return
    
        font = pygame.font.Font(FONT_REGULAR_PATH or None, 36)
        text = font.render("Game Paused", True, COLOR_DUKEBLUE)
        text_rect = text.get_rect()
        text_rect.midbottom = (surface.get_width() // 2, surface.get_height() - 30)
        surface.blit(text, text_rect)