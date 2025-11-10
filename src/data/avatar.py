import logging
import pygame
import carla

from src.core.constants import (
    AVATAR_IMAGE_PATH,
    AVATAR_DISTANCE_FROM_HERO,
    AVATAR_INVULNERABLE_TIME,
    AVATAR_BLOCKED_DURATION,
    AVATAR_TOTAL_LIVES
)
from src.core.avatar_direction import AvatarDirection
from src.data.sounds import Sounds
from src.data.sound_mixer import SoundMixer

class Avatar(pygame.sprite.Sprite):
    def __init__(self, lives=AVATAR_TOTAL_LIVES):
        super().__init__()

        self.lives = lives
        self.current_life = lives

        self.invulnerable = True
        self.spawn_time = pygame.time.get_ticks()

        self.current_wp = None
        self.location = None
        self.last_hero_location = None

        self.relative_lane_offset = 0

        self.absolute_lane_id = None

        self.image = None
        self.rect = None
        self.radius = 15 # pixel for drawing

        # Visual feedback
        self.blocked_flash = False
        self.blocked_flash_start = 0
        self.blocked_duration = AVATAR_BLOCKED_DURATION

    def start(self, hero_wp):
        avatar_wp = hero_wp
        offset = self.relative_lane_offset
        for _ in range(abs(offset)):
            if offset > 0:
                right = avatar_wp.get_right_lane()
                if right and right.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = right
            elif offset < 0:
                left = avatar_wp.get_left_lane()
                if left and left.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = left

        # Move forward by AVATAR_DISTANCE_FROM_HERO meters
        avatar_wp = avatar_wp.next(AVATAR_DISTANCE_FROM_HERO)[0] if avatar_wp.next(AVATAR_DISTANCE_FROM_HERO) else avatar_wp

        self.current_wp = avatar_wp
        self.location = avatar_wp.transform.location
        self.last_hero_location = hero_wp.transform.location
        self.absolute_lane_id = avatar_wp.lane_id
        self.invulnerable = True
        self.spawn_time = pygame.time.get_ticks()

    def update(self, hero_wp=None):
        now = pygame.time.get_ticks()

        # Keep avatar at the correct lane offset from hero
        if hero_wp is not None:
            self.update_location_from_hero(hero_wp)

        # Only update invulnerability state if needed
        if self.invulnerable:
            elapsed = (now - self.spawn_time) / 1000.0
            if elapsed >= AVATAR_INVULNERABLE_TIME:
                self.invulnerable = False
                if self.image.get_alpha() != 255:
                    self.image.set_alpha(255)
            else:
                # Only set alpha if it changes
                alpha = 80 if int(elapsed * 10) % 6 < 3 else 255
                if self.image.get_alpha() != alpha:
                    self.image.set_alpha(alpha)

        # Only update blocked flash if needed
        if self.blocked_flash:
            if now - self.blocked_flash_start <= self.blocked_duration:
                if self.image.get_alpha() != 80:
                    self.image.set_alpha(80)
            else:
                self.blocked_flash = False
                if self.image.get_alpha() != 255:
                    self.image.set_alpha(255)

    def draw(self, surface, world_to_pixel):
        """
        Draw the avatar as a rotated image centered on the map position.
        Only rotate the image if the yaw has changed.
        """
        if not self.current_wp:
            return

        self.location = self.current_wp.transform.location
        x, y = world_to_pixel(self.location)

        if self.image is None:
            self.image = pygame.image.load(AVATAR_IMAGE_PATH).convert_alpha()
            self.rect = self.image.get_rect()
            self.image = pygame.transform.scale(self.image, (self.radius * 2, self.radius * 2))
            self._last_yaw = None
            self._rotated_image = None
            self._rotated_rect = None

        yaw = self.current_wp.transform.rotation.yaw

        # Only rotate if yaw changed
        if getattr(self, '_last_yaw', None) != yaw:
            self._rotated_image = pygame.transform.rotate(self.image, -yaw - 90)
            self._rotated_rect = self._rotated_image.get_rect(center=(x, y))
            self._last_yaw = yaw
        else:
            self._rotated_rect.center = (x, y)

        surface.blit(self._rotated_image, self._rotated_rect)

    def update_location_from_hero(self, hero_wp):
        if not hero_wp:
            logging.warning("Missing hero waypoint.")
            return

        avatar_wp = hero_wp
        offset = self.relative_lane_offset
        for _ in range(abs(offset)):
            if offset > 0:
                right = avatar_wp.get_right_lane()
                if right and right.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = right
            elif offset < 0:
                left = avatar_wp.get_left_lane()
                if left and left.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = left

        # Move forward by AVATAR_DISTANCE_FROM_HERO meters
        avatar_wp = avatar_wp.next(AVATAR_DISTANCE_FROM_HERO)[0] if avatar_wp.next(AVATAR_DISTANCE_FROM_HERO) else avatar_wp

        self.current_wp = avatar_wp
        self.location = avatar_wp.transform.location
        if self.rect:
            self.rect.center = (self.location.x, self.location.y)

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
            if wp.lane_type.name == "Driving":
                return wp

        # No suitable path found
        return None

    def feedback_blocked(self):
        self.blocked_flash = True
        self.blocked_flash_start = pygame.time.get_ticks()
        SoundMixer.instance().play(Sounds.BLOCKED)

    def change_waypoint(self, hero_wp, direction, safety_margin=3.0):
        """
        Change the avatar's relative lane offset or direction.
        Prevents changing offset if the target lane does not exist.
        Adds debug logging and robust lane checks.
        """
        if hero_wp is None:
            logging.warning("Missing hero waypoint.")
            self.feedback_blocked()
            return

        # Find avatar's current waypoint (may be offset from hero)
        avatar_wp = hero_wp
        offset = self.relative_lane_offset
        logging.debug(f"Attempting lane change: current offset={offset}, absolute_lane_id={self.absolute_lane_id}, hero lane_id={hero_wp.lane_id}")

        # Traverse to avatar's current lane from hero_wp
        if offset > 0:
            for _ in range(offset):
                right = avatar_wp.get_right_lane()
                if right and right.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = right
                else:
                    logging.debug("Failed to traverse right for offset.")
                    break
        elif offset < 0:
            for _ in range(-offset):
                left = avatar_wp.get_left_lane()
                if left and left.lane_type.name.lower() == avatar_wp.lane_type.name.lower():
                    avatar_wp = left
                else:
                    logging.debug("Failed to traverse left for offset.")
                    break

        logging.debug(f"Avatar is at lane_id={avatar_wp.lane_id}, lane_type={avatar_wp.lane_type.name}")

        # Check left/right lane existence from avatar's current lane
        if direction == AvatarDirection.LEFT:
            left_wp = avatar_wp.get_left_lane()
            if not left_wp or left_wp.lane_type.name.lower() != avatar_wp.lane_type.name.lower():
                logging.debug("Blocked: No more left lanes available.")
                self.feedback_blocked()
                return
            self.absolute_lane_id = avatar_wp.lane_id - 1
            self.relative_lane_offset -= 1
            logging.debug(f"Avatar lane offset changed to {self.relative_lane_offset} (LEFT), new absolute_lane_id={self.absolute_lane_id}")
            return

        elif direction == AvatarDirection.RIGHT:
            right_wp = avatar_wp.get_right_lane()
            if not right_wp or right_wp.lane_type.name.lower() != avatar_wp.lane_type.name.lower():
                logging.debug("Blocked: No more right lanes available.")
                self.feedback_blocked()
                return
            self.absolute_lane_id = avatar_wp.lane_id + 1
            self.relative_lane_offset += 1
            logging.debug(f"Avatar lane offset changed to {self.relative_lane_offset} (RIGHT), new absolute_lane_id={self.absolute_lane_id}")
            return

        else:
            logging.warning("Unknown direction for avatar.")
            self.feedback_blocked()
            return

    def kill(self):
        """
        Handle the avatar's death logic.
        """
        if self.invulnerable:
            logging.debug("Avatar is invulnerable.")
            return

        SoundMixer.instance().play(Sounds.BLOCKED)

        self.current_life -= 1
        self.invulnerable = True
        self.spawn_time = pygame.time.get_ticks()
        logging.debug(f"Avatar killed! Lives left: {self.current_life}")

        if self.current_life == 0:
            logging.debug("Avatar has no lives left.")
            return True
        
        self.location = self.last_hero_location
        self.rect.center = (self.location.x, self.location.y)

        return None