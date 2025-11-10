import carla
import logging
import pygame
import weakref
import random
import math

# Local imports
from src.engine.traffic_light_surfaces import TrafficLightSurfaces
from src.engine.game_map_image import GameMapImage
from src.utils.util import Util
from src.utils.get_actor_display_name import get_actor_display_name
from src.core.constants import (
    HERO_IMAGE_PATH,
    PIXELS_PER_METER, 
    HERO_DEFAULT_SCALE,
    PIXELS_AHEAD_VEHICLE
)
from src.core.colors import (
    COLOR_AQUAMARINE,
    COLOR_BLACK, 
    COLOR_WHITE,
    COLOR_ALUMINIUM_1,
    COLOR_ALUMINIUM_5,
    COLOR_BUTTER_1,
    COLOR_SCARLET_RED_1,
    COLOR_PLUM_2,
    COLOR_SKY_BLUE_0,
    COLOR_CHOCOLATE_1,
    COLOR_ALUMINIUM_0,
    COLOR_PLUM_0,
    COLOR_TRANSPARENT,
    COLOR_RICHBLACK,
    COLOR_LANE_BACKGROUND
    )


class GameView:
    def __init__(self, args):
        self.args = args
        self.server_fps = 0.0
        self.simulation_time = 0
        self.server_clock = pygame.time.Clock()

        # World data
        self.world = None
        self.town_map = None
        self.actors_with_transform = []

        # Game Manager
        self.game_manager = None

        self._input = None

        self.surface_size = [0, 0]  # Size of the surface to render the map
        self.prev_scaled_size = 0
        self.scaled_size = 0

        # Hero actor
        self.hero_actor = None
        self.spawned_hero = None
        self.hero_transform = None

        # Hero image
        self.hero_image = None
        self.hero_rect = (0, 0)

        self.scale_offset = [0, 0]  # Offset for scaling the map

        # Vehicle ID surface
        self.vehicle_id_surface = None  # Surface for vehicle IDs
        self.result_surface = None  # Surface for results display

        # Traffic light surfaces
        self.traffic_light_surfaces = TrafficLightSurfaces()  # Surface for traffic lights
        self.affected_traffic_light = None  # Traffic light affected by the hero actor

        # Map Info
        self.map_image = None
        self.border_round_surface = None
        self.original_surface_size = None
        self.hero_surface = None
        self.actors_surface = None

    def start(self, input_control, world, town_map, game_manager):
        """
        Builds the game view, stores the needed modules and prepares rendering in Hero Mode.
        """
        if self.hero_image is None:
            self.hero_image = pygame.image.load(HERO_IMAGE_PATH).convert_alpha()

        self.world, self.town_map = world, town_map
        
        self.game_manager = game_manager

        self.map_image = GameMapImage(
            self.world,
            self.town_map,
            PIXELS_PER_METER,
            show_triggers=False,
            show_connections=False,
            show_spawn_points=False
        )

        self._input = input_control

        self.original_surface_size = min(self.args.width, self.args.height)
        self.surface_size = self.map_image.big_map_surface.get_width()

        # Render actors
        self.actors_surface = pygame.Surface((self.map_image.surface.get_width(), self.map_image.surface.get_height()))
        self.actors_surface.set_colorkey(COLOR_BLACK)

        self.vehicle_id_surface = pygame.Surface((self.surface_size, self.surface_size)).convert()
        self.vehicle_id_surface.set_colorkey(COLOR_BLACK)

        # Surface around the circle, must be transparent
        self.border_round_surface = pygame.Surface((self.args.width, self.args.height), pygame.SRCALPHA).convert_alpha()
        self.border_round_surface.set_colorkey(COLOR_WHITE)
        self.border_round_surface.fill(COLOR_TRANSPARENT)

        # Used for Hero Mode, draws the map contained in a circle with white border
        # center_offset = (int(self.args.width / 2), int(self.args.height / 2))
        # pygame.draw.circle(self.border_round_surface, COLOR_ALUMINIUM_1, center_offset, int(self.args.height / 2))
        # pygame.draw.circle(self.border_round_surface, COLOR_WHITE, center_offset, int((self.args.height - 8) / 2))

        # Transparent background for inner circle
        scaled_original_size = self.original_surface_size * (1.0 / 0.9)
        self.hero_surface = pygame.Surface((scaled_original_size, scaled_original_size)).convert_alpha()
        self.hero_surface.fill(COLOR_RICHBLACK)
        self.hero_surface.set_alpha(0.2)

        # Map results, must be visible
        self.result_surface = pygame.Surface((self.surface_size, self.surface_size)).convert()
        self.result_surface.set_colorkey(COLOR_BLACK)

        # Create a circular mask for the hero surface
        circle_mask = pygame.Surface(self.hero_surface.get_size(), pygame.SRCALPHA).convert_alpha()
        circle_radius = min(circle_mask.get_width(), circle_mask.get_height()) // 2
        pygame.draw.circle(circle_mask, (255, 255, 255, 0), (circle_radius, circle_radius), circle_radius)

        self.hero_circle_mask = circle_mask

        # Start hero mode by default
        self.select_hero_actor()
        # self.hero_actor.set_autopilot(False)
        self._input.wheel_offset = HERO_DEFAULT_SCALE
        self._input.control = carla.VehicleControl()

        # Register event for receiving server tick
        weak_self = weakref.ref(self)
        self.world.on_tick(lambda timestamp: GameView.on_world_tick(weak_self, timestamp))

    def select_hero_actor(self):
        """Selects only one hero actor if there are more than one. If there are not any, it will spawn one."""
        hero_vehicles = [actor for actor in self.world.get_actors()
                         if 'vehicle' in actor.type_id and actor.attributes['role_name'] == self.args.rolename]
        if len(hero_vehicles) == 1:
            logging.debug("Selecting the hero")

            self.hero_actor = hero_vehicles[0]
            self.hero_transform = hero_vehicles[0].get_transform()
        if len(hero_vehicles) > 1:
            logging.warning(
                "There are multiple hero vehicles in the world. Selecting the first one found."
            )
            self.hero_actor = hero_vehicles[0]
            self.hero_transform = hero_vehicles[0].get_transform()
        # else:
        #     logging.warning("There is no hero spawning a new one")
        #     self._spawn_hero()

    def _spawn_hero(self):
        """Spawns the hero actor when the script runs"""
        # Get a random blueprint.
        blueprint = random.choice(self.world.get_blueprint_library())
        blueprint.set_attribute('role_name', self.args.rolename)
        if blueprint.has_attribute('color'):
            color = random.choice(blueprint.get_attribute('color').recommended_values)
            blueprint.set_attribute('color', color)
        # Spawn the player.
        while self.hero_actor is None:
            spawn_points = self.world.get_map().get_spawn_points()
            spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
            self.hero_actor = self.world.try_spawn_actor(blueprint, spawn_point)
        self.hero_transform = self.hero_actor.get_transform()

        # Save it in order to destroy it when closing program
        self.spawned_hero = self.hero_actor

    def tick(self):
        """Retrieves the actors for Hero and Map modes and updates de HUD based on that"""
        actors = self.world.get_actors()

        # We store the transforms also so that we avoid having transforms of
        # previous tick and current tick when rendering them.
        self.actors_with_transforms = [(actor, actor.get_transform()) for actor in actors]
        if self.hero_actor is not None:
            self.hero_transform = self.hero_actor.get_transform()

    @staticmethod
    def on_world_tick(weak_self, timestamp):
        """Updates the server tick"""
        self = weak_self()
        if not self:
            return

        self.server_clock.tick()
        self.server_fps = self.server_clock.get_fps()
        self.simulation_time = timestamp.elapsed_seconds

    def _show_nearby_vehicles(self, vehicles):
        """Shows nearby vehicles of the hero actor"""
        info_text = []
        if self.hero_actor is not None and len(vehicles) > 1:
            location = self.hero_transform.location
            vehicle_list = [x[0] for x in vehicles if x[0].id != self.hero_actor.id]

            def distance(v): return location.distance(v.get_location())
            for n, vehicle in enumerate(sorted(vehicle_list, key=distance)):
                if n > 15:
                    break
                vehicle_type = get_actor_display_name(vehicle, truncate=22)
                info_text.append('% 5d %s' % (vehicle.id, vehicle_type))

    def _split_actors(self):
        """Splits the retrieved actors by type id"""
        vehicles = []
        traffic_lights = []
        speed_limits = []
        walkers = []

        for actor_with_transform in self.actors_with_transforms:
            actor = actor_with_transform[0]
            if 'vehicle' in actor.type_id:
                vehicles.append(actor_with_transform)
            elif 'traffic_light' in actor.type_id:
                traffic_lights.append(actor_with_transform)
            elif 'speed_limit' in actor.type_id:
                speed_limits.append(actor_with_transform)
            elif 'walker.pedestrian' in actor.type_id:
                walkers.append(actor_with_transform)

        return (vehicles, traffic_lights, speed_limits, walkers)

    def _render_traffic_lights(self, surface, list_tl, world_to_pixel):
        """Renders the traffic lights and shows its triggers and bounding boxes if flags are enabled"""
        self.affected_traffic_light = None

        for tl in list_tl:
            world_pos = tl.get_location()
            pos = world_to_pixel(world_pos)

            if False: # self.args.show_triggers:
                corners = Util.get_bounding_box(tl)
                corners = [world_to_pixel(p) for p in corners]
                pygame.draw.lines(surface, COLOR_BUTTER_1, True, corners, 2)

            if self.hero_actor is not None:
                corners = Util.get_bounding_box(tl)
                corners = [world_to_pixel(p) for p in corners]
                tl_t = tl.get_transform()

                transformed_tv = tl_t.transform(tl.trigger_volume.location)
                hero_location = self.hero_actor.get_location()
                d = hero_location.distance(transformed_tv)
                s = Util.length(tl.trigger_volume.extent) + Util.length(self.hero_actor.bounding_box.extent)
                if (d <= s):
                    # Highlight traffic light
                    self.affected_traffic_light = tl
                    srf = self.traffic_light_surfaces.surfaces['h']
                    surface.blit(srf, srf.get_rect(center=pos))

            srf = self.traffic_light_surfaces.surfaces[tl.state]
            surface.blit(srf, srf.get_rect(center=pos))

    def _render_speed_limits(self, surface, list_sl, world_to_pixel, world_to_pixel_width):
        """Renders the speed limits by drawing two concentric circles (outer is red and inner white) and a speed limit text"""

        font_size = world_to_pixel_width(2)
        radius = world_to_pixel_width(2)
        font = pygame.font.SysFont('Arial', font_size)

        for sl in list_sl:

            x, y = world_to_pixel(sl.get_location())

            # Render speed limit concentric circles
            white_circle_radius = int(radius * 0.75)

            pygame.draw.circle(surface, COLOR_SCARLET_RED_1, (x, y), radius)
            pygame.draw.circle(surface, COLOR_ALUMINIUM_0, (x, y), white_circle_radius)

            limit = sl.type_id.split('.')[2]
            font_surface = font.render(limit, True, COLOR_ALUMINIUM_5)

            if False: # self.args.show_triggers
                corners = Util.get_bounding_box(sl)
                corners = [world_to_pixel(p) for p in corners]
                pygame.draw.lines(surface, COLOR_PLUM_2, True, corners, 2)

            # Blit
            if self.hero_actor is not None:
                # In hero mode, Rotate font surface with respect to hero vehicle front
                angle = -self.hero_transform.rotation.yaw - 90.0
                font_surface = pygame.transform.rotate(font_surface, angle)
                offset = font_surface.get_rect(center=(x, y))
                surface.blit(font_surface, offset)

            else:
                # In map mode, there is no need to rotate the text of the speed limit
                surface.blit(font_surface, (x - radius / 2, y - radius / 2))

    def _render_walkers(self, surface, list_w, world_to_pixel):
        """Renders the walkers' bounding boxes"""
        for w in list_w:
            color = COLOR_PLUM_0

            # Compute bounding box points
            bb = w[0].bounding_box.extent
            corners = [
                carla.Location(x=-bb.x, y=-bb.y),
                carla.Location(x=bb.x, y=-bb.y),
                carla.Location(x=bb.x, y=bb.y),
                carla.Location(x=-bb.x, y=bb.y)]

            w[1].transform(corners)
            corners = [world_to_pixel(p) for p in corners]
            pygame.draw.polygon(surface, color, corners)

    def _render_vehicles(self, surface, list_v, world_to_pixel):
        """Renders the vehicles' bounding boxes"""
        for v in list_v:
            color = COLOR_AQUAMARINE
            if int(v[0].attributes['number_of_wheels']) == 2:
                color = COLOR_AQUAMARINE
            if v[0].attributes['role_name'] == self.args.rolename:
                # Simple, direct rendering of the hero vehicle
                x, y = world_to_pixel(v[0].get_location())
                angle = (-v[1].rotation.yaw - 90) % 360

                center = (int(x), int(y))
                hero_image_rotated = pygame.transform.rotozoom(self.hero_image, angle, 1.0).convert_alpha()
                hero_rect_rotated = hero_image_rotated.get_rect(center=center)
                surface.blit(hero_image_rotated, hero_rect_rotated)

                if v[1] is not None:
                    self.hero_transform = v[1]


            # Compute bounding box points
            bb = v[0].bounding_box.extent
            corners = [carla.Location(x=-bb.x, y=-bb.y),
                       carla.Location(x=bb.x - 0.8, y=-bb.y),
                       carla.Location(x=bb.x, y=0),
                       carla.Location(x=bb.x - 0.8, y=bb.y),
                       carla.Location(x=-bb.x, y=bb.y),
                       carla.Location(x=-bb.x, y=-bb.y)
                       ]
            v[1].transform(corners)
            corners = [world_to_pixel(p) for p in corners]

            if v[0].attributes['role_name'] != self.args.rolename:
                pygame.draw.polygon(surface, color, corners)

    def render_actors(self, surface, vehicles, traffic_lights, speed_limits, walkers):
        """Renders all the actors"""
        # Static actors
        self._render_traffic_lights(surface, [tl[0] for tl in traffic_lights], self.map_image.world_to_pixel)
        self._render_speed_limits(surface, [sl[0] for sl in speed_limits], self.map_image.world_to_pixel,
                                  self.map_image.world_to_pixel_width)

        # Dynamic actors
        self._render_vehicles(surface, vehicles, self.map_image.world_to_pixel)
        self._render_walkers(surface, walkers, self.map_image.world_to_pixel)

    def clip_surfaces(self, clipping_rect):
        """Used to improve perfomance. Clips the surfaces in order to render only the part of the surfaces that are going to be visible"""
        self.actors_surface.set_clip(clipping_rect)
        self.vehicle_id_surface.set_clip(clipping_rect)
        self.result_surface.set_clip(clipping_rect)

    def _compute_scale(self, scale_factor):
        """Computes the scale and moves the map so that it is zoomed in or out, centered."""
        # Center zooming on the display center
        display_center = (self.args.width / 2, self.args.height / 2)

        # Percentage of surface where center is actually
        px = (display_center[0] - self.scale_offset[0]) / float(self.prev_scaled_size) if self.prev_scaled_size else 0.5
        py = (display_center[1] - self.scale_offset[1]) / float(self.prev_scaled_size) if self.prev_scaled_size else 0.5

        # Offset will be the previously accumulated offset added with the
        # difference of positions in the old and new scales
        diff_between_scales = ((float(self.prev_scaled_size) * px) - (float(self.scaled_size) * px),
                               (float(self.prev_scaled_size) * py) - (float(self.scaled_size) * py))

        self.scale_offset = (self.scale_offset[0] + diff_between_scales[0],
                             self.scale_offset[1] + diff_between_scales[1])

        # Update previous scale
        self.prev_scaled_size = self.scaled_size

        # Scale performed
        self.map_image.scale_map(scale_factor)

    def render(self, display):
        """Renders the map and all the actors in hero and map mode"""
        if self.actors_with_transforms is None:
            return
        self.result_surface.fill(COLOR_TRANSPARENT)

        # Split the actors by vehicle type id
        vehicles, traffic_lights, speed_limits, walkers = self._split_actors()

        # Zoom in and out
        scale_factor = self._input.wheel_offset
        self.scaled_size = int(self.map_image.width * scale_factor)
        if self.scaled_size != self.prev_scaled_size:
            self._compute_scale(scale_factor)

        # Render Actors
        self.actors_surface.fill(COLOR_BLACK)
        self.render_actors(
            self.actors_surface,
            vehicles,
            traffic_lights,
            speed_limits,
            walkers)

        # Show nearby actors from hero mode
        self._show_nearby_vehicles(vehicles)

        # Blit surfaces
        surfaces = ((self.map_image.surface, (0, 0)),
                    (self.actors_surface, (0, 0)),
                    (self.vehicle_id_surface, (0, 0)),
                    )
        
        if self.game_manager.avatar:
            self.game_manager.avatar.draw(self.actors_surface, self.map_image.world_to_pixel)

        self.game_manager.draw_coins(self.actors_surface, self.map_image.world_to_pixel, self.map_image.world_to_pixel_width)

        angle = 0.0 if self.hero_actor is None else self.hero_transform.rotation.yaw + 90.0
        self.traffic_light_surfaces.rotozoom(-angle, self.map_image.scale)

        center_offset = (0, 0)
        if self.hero_actor is not None:
            # Hero Mode
            hero_location_screen = self.map_image.world_to_pixel(self.hero_transform.location)
            hero_front = self.hero_transform.get_forward_vector()
            translation_offset = (
                hero_location_screen[0] - self.hero_surface.get_width() / 2 + hero_front.x * PIXELS_AHEAD_VEHICLE,
                hero_location_screen[1] - self.hero_surface.get_height() / 2 + hero_front.y * PIXELS_AHEAD_VEHICLE
            )

            # Apply clipping rect
            clipping_rect = pygame.Rect(
                translation_offset[0],
                translation_offset[1],
                self.hero_surface.get_width(),
                self.hero_surface.get_height()
            )
            self.clip_surfaces(clipping_rect)

            Util.blits(self.result_surface, surfaces)

            self.border_round_surface.set_clip(clipping_rect)

            # Background for inner circle
            self.hero_surface.fill(COLOR_LANE_BACKGROUND)
            self.hero_surface.blit(
                self.result_surface,
                (-translation_offset[0], -translation_offset[1])
            )

            # --- Create a fixed-size minimap surface ---
            minimap_diameter = min(display.get_width(), display.get_height())
            minimap_surface = pygame.Surface((minimap_diameter, minimap_diameter), pygame.SRCALPHA).convert_alpha()
            minimap_surface.fill((0, 0, 0, 0))  # Fully transparent

            # Rotate the hero surface and center it on the minimap surface
            rotated_hero_surface = pygame.transform.rotozoom(self.hero_surface, angle, 0.9).convert_alpha()
            rotated_rect = rotated_hero_surface.get_rect(center=(minimap_diameter // 2, minimap_diameter // 2))
            minimap_surface.blit(rotated_hero_surface, rotated_rect)

            # Create a fixed-size circular mask
            mask_surface = pygame.Surface((minimap_diameter, minimap_diameter), pygame.SRCALPHA).convert_alpha()
            pygame.draw.circle(
                mask_surface,
                (255, 255, 255, 255),
                (minimap_diameter // 2, minimap_diameter // 2),
                minimap_diameter // 2
            )

            # Apply the mask to the minimap surface
            minimap_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            # Blit the minimap to the display, centered
            center = (display.get_width() // 2 - minimap_diameter // 2, display.get_height() // 2 - minimap_diameter // 2)
            display.blit(minimap_surface, center)

            # Draw the border
            display.blit(self.border_round_surface, (0, 0))
        else:
            # Map Mode
            # Translation offset
            translation_offset = (self._input.mouse_offset[0] * scale_factor + self.scale_offset[0],
                                  self._input.mouse_offset[1] * scale_factor + self.scale_offset[1])
            center_offset = (abs(display.get_width() - self.surface_size) / 2 * scale_factor, 0)

            # Apply clipping rect
            clipping_rect = pygame.Rect(-translation_offset[0] - center_offset[0], -translation_offset[1],
                                        self.args.width, self.args.height)
            self.clip_surfaces(clipping_rect)
            Util.blits(self.result_surface, surfaces)

            display.blit(self.result_surface, (translation_offset[0] + center_offset[0],
                                               translation_offset[1]))            

    def update(self, hero_wp):
        """Updates the game view by rendering the map and actors"""
        self.game_manager.avatar.update(hero_wp)

        vehicles = self.world.get_actors()
        self.game_manager.update(vehicles)

    def destroy(self):
        """Destroy the hero actor when class instance is destroyed"""
        if self.spawned_hero is not None:
            self.spawned_hero.destroy()