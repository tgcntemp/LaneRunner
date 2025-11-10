import carla
import weakref
import numpy as np
import pygame

# Local imports
from src.core.constants import HERO_CAMERA_TRANSFORM

class Camera():
    def __init__(self, parent_actor, display_dimensions):
        self.surface = None
        self._parent = parent_actor
        self.current_frame = None
        bp_library = self._parent.get_world().get_blueprint_library()
        bp = bp_library.find('sensor.camera.rgb')
        bp.set_attribute('image_size_x', str(display_dimensions[0]))
        bp.set_attribute('image_size_y', str(display_dimensions[1]))
        # Set the driver position inside the car
        self.sensor = self._parent.get_world().spawn_actor(bp, HERO_CAMERA_TRANSFORM, attach_to=self._parent)

        # We need to pass the lambda a weak reference to self to avoid
        # circular reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda image: Camera._parse_image(weak_self, image))

    def destroy(self):
        self.sensor.stop()
        self.sensor.destroy()
        self.sensor = None

    def draw_lanes(self, display):
        vehicle_transform = self._parent.get_transform()
        world = self._parent.get_world()
        map = world.get_map()

        # Get the waypoint of the ego vehicle
        ego_wp = map.get_waypoint(vehicle_transform.location, project_to_road=True, lane_type=carla.LaneType.Driving)
        if ego_wp is None:
            return

        # Draw waypoints for ego, left, and right lanes
        lane_waypoints = []
        left_lane_waypoints = []
        right_lane_waypoints = []

        for wp in map.generate_waypoints(20.0):
            if wp.road_id == ego_wp.road_id:
                if wp.lane_id == ego_wp.lane_id:
                    lane_waypoints.append(wp)
                elif wp.lane_id < ego_wp.lane_id:
                    left_lane_waypoints.append(wp)
                elif wp.lane_id > ego_wp.lane_id:
                    right_lane_waypoints.append(wp)

        # Draw left lanes (purple)
        for wp in left_lane_waypoints:
            if wp.transform.location.distance(vehicle_transform.location) < 1000:
                loc = wp.transform.location
                rel_loc = loc - vehicle_transform.location
                x = int(display.get_width() / 2 + rel_loc.y * 10)
                y = int(display.get_height() / 2 - rel_loc.x * 10)
                
                # Draw in 3D world
                # world.debug.draw_point(loc, size=0.15, color=carla.Color(128, 0, 128), life_time=5)

        # Draw right lanes (blue)
        for wp in right_lane_waypoints:
            if wp.transform.location.distance(vehicle_transform.location) < 1000:
                loc = wp.transform.location
                rel_loc = loc - vehicle_transform.location
                x = int(display.get_width() / 2 + rel_loc.y * 10)
                y = int(display.get_height() / 2 - rel_loc.x * 10)
                # Draw in 3D world
                # world.debug.draw_point(loc, size=0.15, color=carla.Color(0, 0, 255), life_time=5)

        # Draw ego lane (green)
        for wp in lane_waypoints:
            if wp.transform.location.distance(vehicle_transform.location) < 1000:
                loc = wp.transform.location
                rel_loc = loc - vehicle_transform.location
                x = int(display.get_width() / 2 + rel_loc.y * 10)
                y = int(display.get_height() / 2 - rel_loc.x * 10)
                # Draw in 3D world
                # world.debug.draw_point(loc, size=0.15, color=carla.Color(0, 255, 0), life_time=5)

    def render(self, display):
        if self.surface is not None:
            display.blit(self.surface, (0, 0))
            self.draw_lanes(display)  # <-- Add this line to overlay lanes

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        self.current_frame = image.frame
        image.convert(carla.ColorConverter.Raw)
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))