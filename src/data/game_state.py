import enum as Enum

class GameState(Enum.Enum):
    """
    Enum representing the different states of the game.
    """
    MANUAL_DRIVING = "manual_driving"
    STARTING = "starting"
    IN_GAME = "in_game"
    PAUSED = "paused"
    TAKEOVER_REQUESTING = "takeover_requesting"
    GAME_OVER = "game_over"
    END_GAME = "end_game"

    def __str__(self):
        return self.value