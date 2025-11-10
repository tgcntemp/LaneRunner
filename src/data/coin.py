import logging
import uuid
import pygame

# Local imports
from src.core.constants import COIN_IMAGE_PATH
from src.data.sounds import Sounds
from src.data.sound_mixer import SoundMixer

class Coin(pygame.sprite.Sprite):
    def __init__(self, wp, value=1, image_path=COIN_IMAGE_PATH):
        """
        Initialize a Coin object with a specific location.
        
        :param wp: The wp of the coin in the world.
        """
        super().__init__()

        self.id = str(uuid.uuid4())
        self.wp = wp
        self.value = value
        self.collected_time = None
        self.collected = False
        self.visible = True

        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect()
        self.coin_radius = 1.0 # meters

    def collect(self):
        """
        Mark the coin as collected and set the collected time.
        """
        if not self.collected:
            self.collected = True
            self.collected_time = pygame.time.get_ticks()
            self.visible = False
            self.kill()  # Remove the coin from all sprite groups
            logging.debug(f"Coin {self.id} collected at {self.collected_time} with value {self.value}")
            SoundMixer.instance().play(Sounds.COIN_COLLECTED)
            return self.value
        
        return 0
    
    def draw(self, display, world_to_pixel, world_to_pixel_width):
        """
        Draw the coin on the display if it is visible.
        
        :param display: The pygame display surface.
        """
        coin_radius_px = max(3, int(world_to_pixel_width(self.coin_radius)))

        if self.visible and not self.collected:
            x, y = world_to_pixel(self.wp.transform.location)

            if self.image is None:
                self.image = pygame.image.load("coin.png").convert_alpha()

            image_rotated = pygame.transform.rotate(self.image, -self.wp.transform.rotation.yaw - 90.0)
            if self.visible:
                display.blit(image_rotated, (x - coin_radius_px, y - coin_radius_px))

    def hide(self):
        """
        Hide the coin by setting its visibility to False.
        """
        self.visible = False
        self.kill()

    def show(self):
        """
        Show the coin by setting its visibility to True.
        """
        self.visible = True
        self.add()

    def reset(self, wp):
        """
        Reset the coin if not collected to new position.
        :param position: The new position for the coin.
        """
        if not self.collected:
            self.wp = wp
            self.rect.center = (self.location.x, self.location.y)
            self.visible = True
            self.add()