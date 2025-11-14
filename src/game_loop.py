import pygame
import logging
import os
import carla
import traceback

# Local imports
from src.views.game_view import GameView
from src.data.game_manager import GameManager
from src.data.game_state import GameState
from src.core.colors import COLOR_AQUAMARINE
from src.core.constants import TITLE_WORLD, FONT_REGULAR_PATH
from src.engine.sensor.input_control import InputControl
from src.engine.world import World
from src.data.sound_mixer import SoundMixer
from src.data.sounds import Sounds
from src.sessions.lanerunner_logger import LaneRunnerLogger

def game_loop(args):
    """
    Main game loop for the LaneRunner.
    This function will be called repeatedly to update the game state.
    """
    logging.debug("Game loop started with arguments: %s", args)

    world = None
    lanerunner_logger = LaneRunnerLogger()

    try:
        # Here you would implement the main game logic
        # For example, connecting to the Carla server, spawning vehicles, etc.
        pygame.init()

        # Initialize the mixer and sounds
        pygame.mixer.init()

        mixer = SoundMixer.instance()
        for sound in Sounds.all():
            try:
                mixer.load_sound(sound)
                logging.debug(f"Loaded sound: {sound.name}")
            except Exception as e:
                logging.error("Failed to load sound %s: %s", sound.name, e)
        logging.debug("Sound mixer initialized with sounds.")

        # Initialize the display
        display = pygame.display.set_mode(
            (args.width, args.height),
            pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption(args.description)

        # Create an overlay surface at 50% of display size
        overlay_width = int(args.width * 0.5)
        overlay_height = int(args.height * 0.5)
        overlay_surface = pygame.Surface((overlay_width, overlay_height), pygame.SRCALPHA)
        overlay_rect = overlay_surface.get_rect(center=(args.width // 3, args.height // 2))

        # Set the font path
        font_path = os.path.join(FONT_REGULAR_PATH)

        font_size = 60  # Default font size

        # Import Montserrat Font
        try:
            # Initialize pygame font
            pygame.font.init()
            font = pygame.font.Font(font_path, font_size)
        except FileNotFoundError:
            logging.error("%s not found. Using default font.", font_path)
        except Exception as e:
            logging.error("An error occurred while loading the font: %s", e)
            # Fallback to default font if Montserrat is not available
            pygame.font.init()
            font = pygame.font.Font(None, font_size)

        text_surface = font.render(
            "Welcome to LaneRunner!", True, COLOR_AQUAMARINE
        )
        display.blit(text_surface, text_surface.get_rect(center=(args.width // 2, args.height // 2)))
        pygame.display.flip()

        try:
            client = carla.Client(args.host, args.port)
            client.set_timeout(2.0)  # Set a timeout for the connection
        except Exception as e:
            logging.error("Failed to connect to Carla server: %s", e)
            return
        
        logging.debug("Connected to Carla server at %s:%d", args.host, args.port)

        # Load the specified map
        try:
            carla_world = client.load_world(args.map)
            town_map = carla_world.get_map()
            logging.debug("Loaded map: %s", args.map)
        except Exception as e:
            logging.error("Failed to load map %s: %s", args.map, e)
            return
        
        logging.debug("Carla world initialized successfully.")

        # Initialize the InputControl and World
        world = World(client, carla_world, args)
        game_view = GameView(args)
        input_control = InputControl(TITLE_WORLD, world, args.autopilot, lanerunner_logger)

        game_manager = GameManager()

        game_view.start(input_control, carla_world, town_map, game_manager)

        hero_wp = town_map.get_waypoint(game_view.hero_transform.location)
        game_manager.start(hero_wp)

        input_control.start(game_manager)

        settings = carla_world.get_settings()
        settings.synchronous_mode = args.sync

        carla_world.apply_settings(settings)
        logging.debug("Game settings applied: Synchronous mode = %s", args.sync)

        # Main Game Loop
        clock = pygame.time.Clock()

        while True:
            clock.tick_busy_loop(60)  # Limit to 60 FPS

            carla_world.tick()
            game_view.tick()
            world.tick()

            current_wp = town_map.get_waypoint(game_view.hero_transform.location)
            
            # Handle eventsgst
            if input_control.parse_events(clock, current_wp):
                return

            
            # Render all modules
            world.render(display)
            lanerunner_logger.render_recording_status(display)

            # Clear overlay before drawing
            overlay_surface.fill((0, 0, 0, 0))  # Transparent fill

            game_state = game_manager.get_state()

            if game_state == GameState.MANUAL_DRIVING:
                pass
            elif game_state == GameState.STARTING:
                delta_time = clock.tick_busy_loop(60) / 1000.0  # Convert milliseconds to seconds
                if game_manager.has_gamified_active:
                    game_manager.update_starting(delta_time, current_wp)
                    game_manager.draw_starting(overlay_surface)
            elif game_state == GameState.IN_GAME:
                if game_manager.has_gamified_active:
                    game_view.render(overlay_surface)
                    game_view.update(current_wp)
                    game_manager.draw_coin_counter(overlay_surface)
                    game_manager.draw_live_counter(overlay_surface)
            elif game_state == GameState.PAUSED:
                game_manager.draw_pause_menu(overlay_surface)
            elif game_state == GameState.TAKEOVER_REQUESTING:
                delta_time = clock.tick_busy_loop(60) / 1000.0  # Convert milliseconds to seconds
                game_manager.update_takeover(delta_time)
                game_manager.draw_takeover_request(overlay_surface)
            elif game_state == GameState.GAME_OVER:
                game_manager.draw_game_over_menu(overlay_surface)
            elif game_state == GameState.END_GAME:
                game_manager.draw_victory_menu(overlay_surface)

            # Blit the overlay onto the main display
            display.blit(overlay_surface, overlay_rect)

            pygame.display.flip()

    # Handle Errors
    except pygame.error as e:
        logging.error("Pygame error: %s", e)
    except KeyboardInterrupt:
        logging.debug("Game loop interrupted by user.")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        if tb:
            filename, lineno, _, _ = tb[-1]
            logging.error(
                "An error occurred in the game loop: %s (File: %s, Line: %d)",
                e, filename, lineno
            )
        else:
            logging.error("An error occurred in the game loop: %s", e)
    finally:

        if world is not None:
            world.destroy()

        pygame.quit()
        logging.debug("Game loop ended.")