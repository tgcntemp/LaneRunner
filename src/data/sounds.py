from enum import Enum

# Local imports
from src.core.constants import SOUND_BASE_PATH

class Sounds(Enum):
    BLOCKED = "blocked"
    COIN_COLLECTED = "coin_collected"
    GAME_OVER = "game_over"
    TAKE_OVER_REQUIRED = "tor_voice"
    TOR_ALERT = "tor_alert"

    @staticmethod
    def all():
        """
        Returns a list of all sound enums.
        """
        return [Sounds.BLOCKED, Sounds.COIN_COLLECTED, Sounds.GAME_OVER, Sounds.TOR_ALERT, Sounds.TAKE_OVER_REQUIRED]

    @staticmethod
    def path(sound_enum):
        """
        Returns the file path for the given sound enum.
        """
        if sound_enum == Sounds.BLOCKED:
            return SOUND_BASE_PATH + "wall_hit.mp3"
        elif sound_enum == Sounds.COIN_COLLECTED:
            return SOUND_BASE_PATH + "coin_collected.mp3"
        elif sound_enum == Sounds.GAME_OVER:
            return SOUND_BASE_PATH + "game_over.mp3"
        elif sound_enum == Sounds.TAKE_OVER_REQUIRED:
            return SOUND_BASE_PATH + "tor_voice.mp3"
        elif sound_enum == Sounds.TOR_ALERT:
            return SOUND_BASE_PATH + "tor_alert.mp3"
        else:
            raise ValueError("Unknown sound enum: {}".format(sound_enum))