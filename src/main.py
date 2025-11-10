#!/usr/bin/env python

"""
=========================================================
Titanic Runner - Carla Control Client
=========================================================

Titanic Runner is a Carla simulator-based game built with Pygame, designed to enhance situation awareness (SA) in Level 3 automated driving vehicles. This project is part of the "Natural User Interfaces - Enhancing Awareness in Autonomous Driving" study for the User Experience M.Sc. at THI.

Please refer to the README.md file for more information about the Titanic Runner project.


=========================================================

=== Titanic Runner Controls ===

    W            : throttle
    S            : brake
    A            : steer left
    D            : steer right
    O            : toggle manual gear shift
    COMMA        : shift down gear (manual)
    PERIOD       : shift up gear (manual)
    Q            : toggle reverse
    Space        : hand-brake

    T            : start session for logging
    Y            : end session and save for logging

    U            : Respawn hero vehicle and reset game

    Z            : request takeover
    X (DISABLED) : manual driving (just for TAKEOVER_REQUESTING state)
    C            : traffic light RED
    V            : traffic light GREEN
    B            : pause/resume game
    N            : restart game
    M            : end game

    K            : enabling autopilot with Not Gamified
    L            : enabling autopilot with Gamified
    P            : disabling autopilot

    ESC          : quit

=========================================================
"""

import argparse
import logging

# Local imports
from src.game_loop import game_loop
from src.core.constants import DESCRIPTION

def main():
    argparser = argparse.ArgumentParser(
        description=DESCRIPTION,
    )

    argparser.add_argument(
        "-d", "--description",
        metavar="DESCRIPTION",
        default=DESCRIPTION,
        help="Description of the Carla Control Client (default: Titanic Runner - Carla Control Client)"
    )

    # General arguments
    argparser.add_argument(
        "-v", "--verbose",
        action="store_true",
        dest="debug",
        help="Enable verbose output"
    )

    # Carla server connection arguments
    argparser.add_argument(
        "--host",
        metavar="H",
        default="127.0.0.1",
        help="IP address of the Carla server (default: 127.0.0.1)"
    )

    argparser.add_argument(
        "-p", "--port",
        metavar="P",
        type=int,
        default=2000,
        help="Port of the Carla server (default: 2000)"
    )

    # Carla client arguments
    argparser.add_argument(
        "--rolename",
        metavar="ROLENAME",
        default="titanic-hero",
        help="Role name for the Carla client (default: titanic-hero)"
    )

    argparser.add_argument(
        "-m", "--map",
        metavar="Town",
        default="Town04",
        help="Map to load in Carla (default: Town04)"
    )

    argparser.add_argument(
        "-a", "--autopilot",
        action="store_true",
        default=False,
        help="Enable autopilot mode"
    )

    argparser.add_argument(
        "-r", "--resolution",
        metavar="WIDTHxHEIGHT",
        default="1280x720",
        help="Resolution of the Carla client window (default: 1280x720)"
    )

    argparser.add_argument(
        "--sync",
        action="store_true",
        default=True,
        help="Enable synchronous mode for the Carla client (default: True)"
    )

    argparser.add_argument(
        '--externalActor',
        action='store_true',
        help='attaches to externally created actor by role name'
    )

    # Scenario arguments
    argparser.add_argument(
        '--start-x',
        type=float,
        default=30.655937,
        help='X coordinate for spawning the actor (default: 30.655937)'
    )
    
    argparser.add_argument(
        '--start-y',
        type=float,
        default=-340.514008,
        help='Y coordinate for spawning the actor (default: -340.514008)'
    )
    
    argparser.add_argument(
        '--dest-x', 
        type=float, 
        default=-90.15,
        help='Destination X coordinate for route visualization (default: -90.15)'
    )
    
    argparser.add_argument(
        '--dest-y', 
        type=float, 
        default=406.44,
        help='Destination Y coordinate for route visualization (default: 406.44)'
    )

    args = argparser.parse_args()

    args.width, args.height = map(int, args.resolution.split('x'))
    
    log_level = logging.DEBUG if args.debug else logging.debug
    logging.basicConfig(format='%(levelname)s: %(message)s', level=log_level)

    logging.debug("Listening for Carla server at %s:%d", args.host, args.port)
    logging.debug("Autopilot mode: %s", "enabled" if args.autopilot else "disabled")
    logging.debug("Client resolution set to %dx%d", args.width, args.height)

    logging.debug("Starting Carla Control Client...")
    logging.debug(__doc__)

    game_loop(args)