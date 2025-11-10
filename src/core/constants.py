import carla

# General Constants
TITLE_WORLD = "Titanic Runner - UXDM_NUI"
DESCRIPTION = "Titanic Runner - Carla Control Client"

# Carla Constants
# CARLA_VEHICLE = "vehicle.tesla.cybertruck"
CARLA_VEHICLE = "vehicle.nissan.patrol_2021"

ASSETS_PATH = "src/assets"
# Font Constants
FONT_LIGHT_PATH = ASSETS_PATH + "/fonts/Montserrat/static/Montserrat-Light.ttf"
FONT_REGULAR_MONTSERRAT_PATH = ASSETS_PATH + "/fonts/Montserrat/static/Montserrat-Regular.ttf"
FONT_REGULAR_PATH = ASSETS_PATH + "/fonts/Goldman/Goldman-Regular.ttf"
FONT_BOLD_PATH = ASSETS_PATH + "/fonts/Goldman/Goldman-Bold.ttf"

# Image Constants
AVATAR_IMAGE_PATH = ASSETS_PATH + "/images/avatar.png"
COIN_IMAGE_PATH = ASSETS_PATH + "/images/coin.png"
HERO_IMAGE_PATH = ASSETS_PATH + "/images/hero.png"

COIN_COUNTER_ICON_PATH = ASSETS_PATH + "/images/coin_counter_icon.png"
CORNER_BOTTOM_RIGHT_PATH = ASSETS_PATH + "/images/corner_bottom_right.png"
CORNER_TOP_LEFT_PATH = ASSETS_PATH + "/images/corner_top_left.png"
MENU_BACKGROUND_PATH = ASSETS_PATH + "/images/menu_background.png"
MENU_HEADER_BACKGROUND_PATH = ASSETS_PATH + "/images/menu_header_background.png"
BUTTON_BACKGROUND_PATH = ASSETS_PATH + "/images/button_background.png"
HEART_FILLED_PATH = ASSETS_PATH + "/images/heart_filled.png"
HEART_EMPTY_PATH = ASSETS_PATH + "/images/heart_empty.png"

# Sound Constants
SOUND_BASE_PATH = ASSETS_PATH + "/sounds/"

# Game Constants
AVATAR_DISTANCE_FROM_HERO = 12.5 # Distance from hero to avatar in meters
AVATAR_INVULNERABLE_TIME = 3  # Time in seconds for avatar invulnerability
AVATAR_BLOCKED_DURATION = 300  # Duration in milliseconds for avatar blocked state
AVATAR_COLLISION_RADIUS = 2.0
AVATAR_TOTAL_LIVES = 3
PIXELS_PER_METER = 12 # Number of pixels per meter for display scaling
PIXELS_AHEAD_VEHICLE = 150
HERO_DEFAULT_SCALE = 1.0  # Default scale for hero actor in Hero Mode
INITIAL_COIN_DISTANCE_FROM_AVATAR = 7.5  # Distance from hero to coin in meters
COIN_SPACING = 20.0  # Spacing between coins in meters
COIN_NUMBER = 5  # Number of coins to spawn
COIN_COLLISION_RADIUS = 2.0  # Radius for coin collision detection in meters
COIN_REMOVE_THRESHOLD = 30.0  # Distance from avatar to remove coin in meters
TAKE_OVER_COUNTDOWN = 3
STARTING_COUNTDOWN = 3  # Starting countdown before the game begins
TARGET_TRAFFIC_LIGHT_ID = 145

# CAMERA TRANSFORMS
## tesla.cybertruck
# HERO_CAMERA_TRANSFORM = carla.Transform(carla.Location(x=0.40, y=-0.25, z=1.80), carla.Rotation(pitch=8.0))
## vehicle.nissan.patrol_2021
HERO_CAMERA_TRANSFORM = carla.Transform(carla.Location(x=0.35, y=-0.25, z=1.65), carla.Rotation(pitch=8.0))

# SPAWN TRANSFORMS
# HERO_SPAWN_TRANSFORM = None 
## Manually set spawn transform for the hero vehicle
HERO_SPAWN_TRANSFORM = carla.Transform(carla.Location(x=-67.140518, y=30.5, z=10.458009), carla.Rotation(pitch=0.972154, yaw=0.076826, roll=0.000000))
# Waypoint(Transform(Location(x=-12.019703, y=-273.314667, z=0.000000), Rotation(pitch=360.000000, yaw=120.025604, roll=0.000000)))