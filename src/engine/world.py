import logging
import random
import carla
import pygame


# Local imports
from src.utils.exit_game import exit_game
from src.core.constants import CARLA_VEHICLE, HERO_SPAWN_TRANSFORM, FONT_REGULAR_PATH
from src.utils.find_weather_presets import find_weather_presets
from src.engine.sensor.collision_sensor import CollisionSensor
from src.engine.sensor.lane_invasion_sensor import LaneInvasionSensor
from src.engine.sensor.gnss_sensor import GnssSensor
from src.engine.sensor.sensor_camera import SensorCamera

class World():
    def __init__(self, client, carla_world, args):
        self.client = client
        self.world = carla_world
        self.sync = args.sync
        self.actor_role_name = args.rolename
        self.dimensions = (args.width, args.height)
        self.args = args

        try:
            self.map = self.world.get_map()
            logging.debug("Map loaded successfully: %s", self.map.name)
        except RuntimeError as e:
            logging.error("RuntimeError: {}".format(e))
            logging.error("The server could not send the OpenDRIVE (.xodr) file:")
            logging.error("Make sure it exists, has the same name of your town, and is correct.")
            exit_game(1)

        self.player = None

        self.trafficmanager = None
        self.collision_sensor = None
        self.lane_invasion_sensor = None
        self.gnss_sensor = None
        self.sensor_camera = None
        self._weather_presets = find_weather_presets()
        self.weather_index = 0

        self.traffic_lights = None

        logging.debug("Loading world with role name: %s", self.actor_role_name)

        self.weather = carla.WeatherParameters(
            cloudiness=0.0, 
            precipitation=0.0, 
            precipitation_deposits=0.0, 
            wind_intensity=0.0, 
            sun_azimuth_angle=0.0, 
            sun_altitude_angle=70.0, 
            fog_density=0.0, 
            fog_distance=0.0, 
            fog_falloff=0.0, 
            wetness=0.0, 
            scattering_intensity=0.0, 
            mie_scattering_scale=0.0, 
            rayleigh_scattering_scale=0.03310000151395798, 
            dust_storm=0.0
        )
    
        self.restart()

    def restart(self):

        self.world.set_weather(self.weather)

        cam_index = self.sensor_camera.index if self.sensor_camera is not None else 0
        cam_pos_index = self.sensor_camera.transform_index if self.sensor_camera is not None else 0

        self.player_max_speed = 1.589
        self.player_max_speed_fast = 3.713

        # Remove all actors with the role_name == self.actor_role_name
        actors = self.world.get_actors().filter('vehicle.*')
        for actor in actors:
            if actor.attributes.get('role_name') == self.actor_role_name:
                logging.debug("Destroying existing actor with role name: %s", self.actor_role_name)
                actor.destroy()
            if actor.attributes.get('base_type') == 'motorcycle' or actor.attributes.get('base_type') == 'bicycle':
                logging.debug("Destroying existing motorcycle/bicycle actor: %s", actor.id)
                actor.destroy()

        blueprint = self.world.get_blueprint_library().find(CARLA_VEHICLE)
        logging.debug("Spawning vehicle with blueprint: %s", blueprint.id)
        blueprint.set_attribute('role_name', self.actor_role_name)
        if blueprint.has_attribute('color'):
            color = "0, 0, 0"
            blueprint.set_attribute('color', color)
        if blueprint.has_attribute('driver_id'):
            driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
            blueprint.set_attribute('driver_id', driver_id)
        if blueprint.has_attribute('is_invincible'):
            blueprint.set_attribute('is_invincible', 'true')
        # Spawn the player.
        if self.player is not None:
            spawn_point = self.player.get_transform()
            spawn_point.location.z += 2.0
            spawn_point.rotation.roll = 0.0
            spawn_point.rotation.pitch = 0.0
            self.destroy()
            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
            self.show_vehicle_telemetry = False
            self.modify_vehicle_physics(self.player)
        
        while self.player is None:
            if not self.map.get_spawn_points():
                logging.debug('There are no spawn points available in your map/town.')
                logging.debug('Please add some Vehicle Spawn Point to your UE4 scene.')
                exit_game(1)
            
            if self.args.start_x is not None and self.args.start_y is not None:
                # Use the provided start coordinates for spawning
                target_location = carla.Location(x=self.args.start_x, y=self.args.start_y, z=0.0)

                waypoint = self.map.get_waypoint(target_location, project_to_road=True, lane_type=carla.LaneType.Driving)
                spawn_point = waypoint.transform if waypoint else carla.Transform(target_location)
                spawn_point.location.z += 0.5  # Adjust height for the vehicle
            else:
                spawn_points = self.map.get_spawn_points()
                spawn_point = HERO_SPAWN_TRANSFORM
                if spawn_point is None:
                    spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
                
            logging.debug("Spawn point: %s", spawn_point)

            self.player = self.world.try_spawn_actor(blueprint, spawn_point)
            self.show_vehicle_telemetry = False
            self.modify_vehicle_physics(self.player)

        self.trafficmanager = self.client.get_trafficmanager(8000)
        self.trafficmanager.set_synchronous_mode(self.args.sync)

        # Set up the sensors.
        self.collision_sensor = CollisionSensor(self.player)
        self.lane_invasion_sensor = LaneInvasionSensor(self.player)
        self.gnss_sensor = GnssSensor(self.player)
        self.sensor_camera = SensorCamera(self.player, self.args)
        self.sensor_camera.transform_index = cam_pos_index
        self.sensor_camera.set_sensor(cam_index, notify=False)
        ############################
        self.traffic_lights = self.world.get_actors().filter('traffic.traffic_light')
        ############################

        logging.debug("Player spawned successfully: %s", self.player.id)

    def modify_vehicle_physics(self, actor):
        #If actor is not a vehicle, we cannot use the physics control
        try:
            physics_control = actor.get_physics_control()
            physics_control.use_sweep_wheel_collision = True
            actor.apply_physics_control(physics_control)
        except Exception:
            pass

    def tick(self):
        """
        Update the world and all actors.
        """
        pass
        # <3
        # if self.player is None or not hasattr(self.player, "get_location"):
        #     return

        # try:
        #     # get current location of the ego vehicle
        #     cur_location = self.player.get_location()
        #     # ===== Draw Route to Destination if provided =====
        #     if self.args.dest_x is not None and self.args.dest_y is not None:
        #         destination = carla.Location(x=self.args.dest_x, y=self.args.dest_y, z=cur_location.z)
        #         route = self._planner.trace_route(cur_location, destination)
        #         if route:  # Check if the route is not empty
        #             num_waypoints_ahead_color = 15  # Change this if you want less look ahead

        #             for i, (wp_data, _) in enumerate(route): # wp_data is a carla.Waypoint
        #                 waypoint_location = wp_data.transform.location + carla.Location(z=0.5)
                        
        #                 point_color = carla.Color(r=0, g=0, b=255)  # Default: Blue for the rest of the route

        #                 if i < num_waypoints_ahead_color:
        #                     point_color = carla.Color(r=0, g=255, b=0)  # Green for the first N waypoints
                        
        #                 # Special color for the last waypoint of the planned route path
        #                 if i == len(route) - 1:
        #                     point_color = carla.Color(r=255, g=255, b=0)  # Yellow for the end of the route path
                        
        #                 # You can use draw_string or draw_point. draw_point is common for paths.
        #                 self.world.debug.draw_point(
        #                     waypoint_location,
        #                     size=0.1,
        #                     color=point_color,
        #                     life_time=0.3,  # Adjust as needed, longer than a tick to see a segment
        #                     persistent_lines=False
        #                 )

        #             # Draw the final destination marker 
        #             self.world.debug.draw_point(
        #                 destination + carla.Location(z=0.5),
        #                 size=0.3,  # Make it a bit larger to be distinct
        #                 color=carla.Color(255, 0, 0),  # Red for the final target marker
        #                 life_time=2.0, # Keep it visible for a couple of seconds
        #                 persistent_lines=False
        #             )

        # except Exception as e:
        #     logging.error(f"[Route Visualization Error] {e}")

        #########
        # ===== Changing lanes to the left when the vehicle is in a traffic jam =====
        # try:
        #     if self.player.get_velocity().length() < 0.1:  # Speed almost 0
        #         current_wp = self.map.get_waypoint(self.player.get_location(), project_to_road=True, lane_type=carla.LaneType.Driving)
        #         if current_wp is not None:
        #             left_wp = current_wp.get_left_lane()
        #             if (
        #                 left_wp is not None
        #                 and left_wp.lane_type == carla.LaneType.Driving
        #                 and left_wp.lane_change in [carla.LaneChange.Left, carla.LaneChange.Both]
        #             ):
        #                 ##self.perform_lane_change(left_wp.transform)
        #                 self.player.set_transform(left_wp.transform)


        #                 logging.debug("↪ Changing lanes to the left performed (manually in traffic jam).")
        # except RuntimeError as e:
        #     logging.error(f"[Lane Change Error] {e}")
        # ########

    def render(self, display):
        """
        Render the world and all actors.
        """
        self.sensor_camera.render(display)
        self.render_speedometer(display)

    def render_speedometer(self, display):
        """
        Render the speedometer for the player vehicle.
        """
        if self.player is not None and hasattr(self.player, 'get_velocity'):
            velocity = self.player.get_velocity()
            speed = (velocity.x**2 + velocity.y**2 + velocity.z**2)**0.5 * 3.6 # Convert m/s to km/h
            speed_text = f"{int(speed)} km/h"
            font_size = 32
            font = pygame.font.Font(FONT_REGULAR_PATH, font_size)
            text_surface = font.render(speed_text, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(self.dimensions[0] // 2 - 150, self.dimensions[1] - 150)) # Slightly shifted to the left and above the bottom
            display.blit(text_surface, text_rect)

    def respawn_player(self):
        """
        Respawn the player vehicle at the initial spawn point.
        Remove nearby vehicles to avoid collision.
        """
        if self.player is not None:
            logging.debug("Respawning player vehicle.")
            if self.args.start_x is not None and self.args.start_y is not None:
                # Use the provided start coordinates for respawning
                target_location = carla.Location(x=self.args.start_x, y=self.args.start_y, z=0.0)
                waypoint = self.map.get_waypoint(target_location, project_to_road=True, lane_type=carla.LaneType.Driving)
                spawn_point = waypoint.transform if waypoint else carla.Transform(target_location)
                spawn_point.location.z += 0.5

                # Remove vehicles near the respawn point
                radius = 5.0  # meters, adjust as needed
                actors = self.world.get_actors().filter('vehicle.*')
                for actor in actors:
                    if actor.id != self.player.id:
                        distance = actor.get_location().distance(spawn_point.location)
                        if distance < radius:
                            logging.debug(f"Destroying vehicle {actor.id} at distance {distance:.2f}m from respawn point.")
                            actor.destroy()

                self.player.set_transform(spawn_point)
        else:
            logging.warning("No player vehicle to respawn.")

    def destroy(self):
        """
        Clean up the world and all actors.
        """
        sensors = [
            self.sensor_camera.sensor,
            self.collision_sensor.sensor,
            self.lane_invasion_sensor.sensor,
            self.gnss_sensor.sensor,
        ]

        for sensor in sensors:
            if sensor:
                sensor.destroy()

        if self.player:
            self.player.destroy()