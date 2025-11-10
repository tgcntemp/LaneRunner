# sound_mixer.py
from src.data.sounds import Sounds

class SoundMixer():
    _instance = None

    def __init__(self):
        if SoundMixer._instance is not None:
            raise Exception("Use SoundMixer.get_instance()")
        self.sounds = {}  # Map: Sounds.BLOCKED -> pygame.mixer.Sound(...)
        SoundMixer._instance = self

    @staticmethod
    def instance():
        if SoundMixer._instance is None:
            SoundMixer()
        return SoundMixer._instance

    def load_sound(self, sound_enum):
        import pygame
        self.sounds[sound_enum] = pygame.mixer.Sound(Sounds.path(sound_enum))

    def play(self, sound_enum):
        if sound_enum in self.sounds:
            self.sounds[sound_enum].play()