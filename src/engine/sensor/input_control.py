import carla
import pygame
import logging
import math

from configparser import ConfigParser

# Local imports
from src.core.constants import TARGET_TRAFFIC_LIGHT_ID
from src.data.game_state import GameState
from src.utils.exit_game import exit_game
from src.core.avatar_direction import AvatarDirection
from src.utils.log_lanerunner_timestamp import log_lanerunner_timestamp

# Import PyGame constants
try:
    import pygame
    from pygame.locals import KMOD_CTRL
    from pygame.locals import K_COMMA
    from pygame.locals import K_DOWN
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_LEFT
    from pygame.locals import K_PERIOD
    from pygame.locals import K_RIGHT
    from pygame.locals import K_SPACE
    from pygame.locals import K_UP
    from pygame.locals import K_a
    from pygame.locals import K_d
    from pygame.locals import K_p
    from pygame.locals import K_o
    from pygame.locals import K_q
    from pygame.locals import K_s
    from pygame.locals import K_w
    from pygame.locals import K_t
    from pygame.locals import K_y
    from pygame.locals import K_u
    from pygame.locals import K_z
    from pygame.locals import K_x
    from pygame.locals import K_c
    from pygame.locals import K_v
    from pygame.locals import K_b
    from pygame.locals import K_n
    from pygame.locals import K_m
    from pygame.locals import K_k
    from pygame.locals import K_l
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')

class InputControl():
    def __init__(self, name, world, autopilot_enabled, lanerunner_logger):
        """Initialize the InputControl with a name."""
        self.name = name
        self._autopilot_enabled = autopilot_enabled
        self.world = world
        self.game_manager = None
        self.lanerunner_logger = lanerunner_logger

        if isinstance(self.world.player, carla.Vehicle):
            self._control = carla.VehicleControl()
            self.world.player.set_autopilot(self._autopilot_enabled)
        else:
            raise NotImplementedError(
                f"InputControl not implemented for {type(self.world.player)}"
            )
        
        self._steer_cache = 0.0
        
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()
        self._joystick_connected = joystick_count > 0

        if joystick_count > 1:
            raise RuntimeError(
                "Multiple joysticks detected. Please use only one joystick."
            )
        
        if self._joystick_connected:
            self._joystick = pygame.joystick.Joystick(0)
            self._joystick.init()

            self._parser = ConfigParser()
            self._parser.read('wheel_config.ini')
            self._steer_idx = int(
                self._parser.get('G29 Racing Wheel', 'steering_wheel'))
            self._throttle_idx = int(self._parser.get('G29 Racing Wheel', 'throttle'))
            self._brake_idx = int(self._parser.get('G29 Racing Wheel', 'brake'))
            self._reverse_idx = int(self._parser.get('G29 Racing Wheel', 'reverse'))
            self._handbrake_idx = int(self._parser.get('G29 Racing Wheel', 'handbrake'))

        self._takeover_pending = False
        self._stab_collecting = False
        self._stab_start_time = None
        self._stab_steer_values = []

    def start(self, game_manager):
        """Start the InputControl with a GameManager."""
        self.game_manager = game_manager
        logging.debug('InputControl started with GameManager')

    def parse_events(self, clock, hero_wp):
        """Parse events from the joystick and update the vehicle control."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()
            elif self._joystick_connected and event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    self.world.restart()
                elif event.button == self._reverse_idx:
                    self._control.gear = 1 if self._control.reverse else -1

            elif event.type == pygame.KEYUP:
                if self._is_quit_shortcut(event.key):
                    exit_game()
                if isinstance(self._control, carla.VehicleControl):
                    if event.key == K_q:
                        self._control.gear = 1 if self._control.reverse else -1
                    elif event.key == K_o:
                        self._control.manual_gear_shift = not self._control.manual_gear_shift
                        self._control.gear = self.world.player.get_control().gear
                        logging.debug('Manual gear shift: %s', self._control.manual_gear_shift)
                    elif self._control.manual_gear_shift and event.key == K_COMMA:
                        self._control.gear = max(-1, self._control.gear - 1)
                    elif self._control.manual_gear_shift and event.key == K_PERIOD:
                        self._control.gear = self._control.gear + 1
                    elif event.key == K_p:
                        self._autopilot_enabled = False
                        self.world.player.set_autopilot(self._autopilot_enabled)
                        logging.debug('Autopilot %s', 'On' if self._autopilot_enabled else 'Off')
                        if self._autopilot_enabled:
                            self.game_manager.start_game()
                    elif event.key == K_LEFT:
                        self.on_scroll_left(hero_wp, self.game_manager.avatar)
                    elif event.key == K_RIGHT:
                        self.on_scroll_right(hero_wp, self.game_manager.avatar)
                    elif event.key == K_UP:
                        # self.on_scroll_up(hero_wp, self.game_manager.avatar)
                        pass
                    elif event.key == K_DOWN:
                        # self.on_scroll_down(hero_wp, self.game_manager.avatar)
                        pass
                    elif event.key == K_t:
                        self.lanerunner_logger.start_session()
                    elif event.key == K_y:
                        self.lanerunner_logger.save_session()
                    elif event.key == K_u:
                        # TODO: - ADD LOGIC TO REMOVE THE VEHICLES IN THAT AREA!!!!
                        # TODO: - Add logic for respawn hero vehicle and reset game
                        self._autopilot_enabled = False
                        self.world.player.set_autopilot(self._autopilot_enabled)
                        self.world.respawn_player()
                        self.game_manager.new_game(hero_wp)
                        self.game_manager.game_state = GameState.MANUAL_DRIVING
                    elif event.key == K_z:
                        self.game_manager.request_takeover()
                        self.lanerunner_logger.add_value(tor_time=log_lanerunner_timestamp())
                        self._takeover_pending = True
                        logging.debug('Take over initialization triggered')
                    elif event.key == K_x:
                        pass
                        # if self.game_manager.game_state != GameState.TAKEOVER_REQUESTING:
                        #     logging.warning("Can not taking over")
                        #     continue
                        # logging.debug("Taking over by user")
                        # self._autopilot_enabled = False
                        # self.world.player.set_autopilot(self._autopilot_enabled)
                        # self.game_manager.game_state = GameState.MANUAL_DRIVING
                        # if self.game_manager.has_gamified_active:
                        #     self.lanerunner_logger.add_value(takeover_time=log_lanerunner_timestamp())
                    elif event.key == K_c:
                        logging.debug('Traffic light control triggered to go RED')
                        for light in self.world.traffic_lights:
                            light.set_state(carla.TrafficLightState.Red)
                            # light.freeze(True)
                    elif event.key == K_v:
                        logging.debug('Traffic light control triggered to go GREEN')
                        for light in self.world.traffic_lights:
                            if light.id == TARGET_TRAFFIC_LIGHT_ID:
                                light.set_state(carla.TrafficLightState.Green)
                                # light.freeze(True)
                    elif event.key == K_b:
                        logging.debug('Toggle pause and resume')
                        self.game_manager.toggle_game()
                    elif event.key == K_n:
                        logging.debug('Restarting the game')
                        self.game_manager.restart_game()
                    elif event.key == K_m:
                        logging.debug('Ending the game')
                        self.game_manager.end_game()
                    elif event.key == K_k:
                        logging.debug("Not gamified version activated")
                        self.game_manager.has_gamified_active = False

                        self._autopilot_enabled = True
                        self.world.player.set_autopilot(self._autopilot_enabled)
                        logging.debug('Autopilot %s', 'On' if self._autopilot_enabled else 'Off')
                        if self._autopilot_enabled:
                            self.game_manager.start_game()
                    elif event.key == K_l:
                        logging.debug("Gamified version activated")
                        logging.debug("Not gamified version activated")
                        self.game_manager.has_gamified_active = True

                        self._autopilot_enabled = True
                        self.world.player.set_autopilot(self._autopilot_enabled)
                        logging.debug('Autopilot %s', 'On' if self._autopilot_enabled else 'Off')
                        if self._autopilot_enabled:
                            self.game_manager.start_game()
                    


            # --- Tablet/External Device Scroll Support ---
            elif event.type == pygame.MOUSEWHEEL:
                # event.x: left/right, event.y: up/down
                if event.x < 0:
                    self.on_scroll_left(hero_wp, self.game_manager.avatar)
                elif event.x > 0:
                    self.on_scroll_right(hero_wp, self.game_manager.avatar)
                if event.y > 0:
                    # self.on_scroll_up(hero_wp, self.game_manager.avatar)
                    pass
                elif event.y < 0:
                    # self.on_scroll_down(hero_wp, self.game_manager.avatar)
                    pass

        if not self._autopilot_enabled:
            if isinstance(self._control, carla.VehicleControl):
                self._parse_vehicle_keys(pygame.key.get_pressed(), clock.get_time())
                if self._joystick_connected:
                    self._parse_vehicle_wheel()
                self._control.reverse = self._control.gear < 0
            elif isinstance(self._control, carla.WalkerControl):
                self._parse_walker_keys(pygame.key.get_pressed(), clock.get_time())
            self.world.player.apply_control(self._control)
        
            if self.game_manager.game_state == GameState.END_GAME:
                self.game_manager.game_state = GameState.END_GAME
            else:
                self.game_manager.game_state = GameState.MANUAL_DRIVING
        else:
            # TODO: - Fix here!!!!!!
            if self.game_manager.game_state == GameState.STARTING:
                self.game_manager.game_state = GameState.STARTING
            elif self.game_manager.game_state == GameState.PAUSED:
                self.game_manager.game_state = GameState.PAUSED
            elif self.game_manager.game_state == GameState.TAKEOVER_REQUESTING:
                self.game_manager.game_state = GameState.TAKEOVER_REQUESTING
            elif self.game_manager.game_state == GameState.MANUAL_DRIVING:
                self.game_manager.game_state = GameState.MANUAL_DRIVING
                self._autopilot_enabled = False
                self.world.player.set_autopilot(self._autopilot_enabled)
            elif self.game_manager.game_state == GameState.GAME_OVER:
                self.game_manager.game_state = GameState.GAME_OVER
            elif self.game_manager.game_state == GameState.END_GAME:
                self.game_manager.game_state = GameState.END_GAME
            else:
                self.game_manager.game_state = GameState.IN_GAME

    # --- Tablet/External Device Scroll Handlers ---
    def on_scroll_left(self, hero_wp, avatar):
        if self.game_manager.game_state != GameState.IN_GAME:
            logging.debug('Scroll Left ignored, not in game state')
            return
        logging.debug('Scroll Left detected (tablet/external device)')
        avatar.change_waypoint(hero_wp, AvatarDirection.LEFT)

    def on_scroll_right(self, hero_wp, avatar):
        if self.game_manager.game_state != GameState.IN_GAME:
            logging.debug('Scroll Right ignored, not in game state')
            return
        logging.debug('Scroll Right detected (tablet/external device)')
        avatar.change_waypoint(hero_wp, AvatarDirection.RIGHT)

    def on_scroll_up(self, hero_wp, avatar):
        if self.game_manager.game_state != GameState.IN_GAME:
            logging.debug('Scroll Up ignored, not in game state')
            return
        logging.debug('Scroll Up detected (tablet/external device)')

    def on_scroll_down(self, hero_wp, avatar):
        if self.game_manager.game_state != GameState.IN_GAME:
            logging.debug('Scroll Down ignored, not in game state')
            return
        logging.debug('Scroll Down detected (tablet/external device)')

    def _parse_vehicle_keys(self, keys, milliseconds):
        self._control.throttle = 1.0 if keys[K_w] else 0.0
        steer_increment = 5e-4 * milliseconds
        if keys[K_a]:
            self._steer_cache -= steer_increment
        elif keys[K_d]:
            self._steer_cache += steer_increment
        else:
            self._steer_cache = 0.0
        self._steer_cache = min(0.7, max(-0.7, self._steer_cache))
        self._control.steer = round(self._steer_cache, 1)
        self._control.brake = 1.0 if keys[K_s] else 0.0
        self._control.hand_brake = keys[K_SPACE]

        # Detect first manual input after TOR
        # if self.game_manager.has_gamified_active:
        if self._takeover_pending and (
            keys[K_w] or keys[K_a] or keys[K_d] or keys[K_s] or keys[K_SPACE]
        ):
            self.lanerunner_logger.add_value(takeover_time=log_lanerunner_timestamp())
            self._takeover_pending = False  # Prevent multiple logs
            logging.info("Takeover time logged from manual input.")
            # Start stability collection
            self._stab_collecting = True
            self._stab_start_time = pygame.time.get_ticks()
            self._stab_steer_values = []

        if self._stab_collecting:
            now = pygame.time.get_ticks()
            elapsed = (now - self._stab_start_time) / 1000.0  # seconds
            self._stab_steer_values.append(self._control.steer)
            if elapsed >= 3.0:
                self.lanerunner_logger.add_value(
                    stab_start=self._stab_start_time,
                    stab_end=now,
                    steer_values=self._stab_steer_values
                )
                self._stab_collecting = False

    def _parse_vehicle_wheel(self):
        numAxes = self._joystick.get_numaxes()
        jsInputs = [float(self._joystick.get_axis(i)) for i in range(numAxes)]

        jsButtons = [float(self._joystick.get_button(i)) for i in
                     range(self._joystick.get_numbuttons())]

        # Custom function to map range of inputs [1, -1] to outputs [0, 1] i.e 1 from inputs means nothing is pressed
        # For the steering, it seems fine as it is
        K1 = 1.0  # 0.55
        steerCmd = K1 * math.tan(1.1 * jsInputs[self._steer_idx])

        K2 = 1.6  # 1.6
        throttleCmd = K2 + (2.05 * math.log10(
            -0.7 * jsInputs[self._throttle_idx] + 1.4) - 1.2) / 0.92
        if throttleCmd <= 0:
            throttleCmd = 0
        elif throttleCmd > 1:
            throttleCmd = 1

        brakeCmd = 1.6 + (2.05 * math.log10(
            -0.7 * jsInputs[self._brake_idx] + 1.4) - 1.2) / 0.92
        if brakeCmd <= 0:
            brakeCmd = 0
        elif brakeCmd > 1:
            brakeCmd = 1

        self._control.steer = steerCmd
        self._control.brake = brakeCmd
        self._control.throttle = throttleCmd

        self._control.hand_brake = bool(jsButtons[self._handbrake_idx])

        manual_input = (
            abs(steerCmd) > 0.05 or throttleCmd > 0.05 or brakeCmd > 0.05 or jsButtons[self._handbrake_idx]
        )

        # if self.game_manager.has_gamified_active:
        if self._takeover_pending and manual_input:
            self.lanerunner_logger.add_value(takeover_time=log_lanerunner_timestamp())
            self._takeover_pending = False
            logging.info("Takeover time logged from wheel input.")
            # Start stability collection
            self._stab_collecting = True
            self._stab_start_time = pygame.time.get_ticks()
            self._stab_steer_values = []

        if self._stab_collecting:
            now = pygame.time.get_ticks()
            elapsed = (now - self._stab_start_time) / 1000.0  # seconds
            self._stab_steer_values.append(self._control.steer)
            if elapsed >= 3.0:
                self.lanerunner_logger.add_value(
                    stab_start=self._stab_start_time,
                    stab_end=now,
                    steer_values=self._stab_steer_values
                )
                self._stab_collecting = False

    @staticmethod
    def _is_quit_shortcut(key):
        return (key == K_ESCAPE) or (key == K_q and pygame.key.get_mods() & KMOD_CTRL)