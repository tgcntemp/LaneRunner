import sys
import pygame
import logging

def exit_game(exit_code=0):
    """Shuts down program and PyGame."""
    pygame.quit()
    logging.debug("Game exited successfully.")
    sys.exit(exit_code)