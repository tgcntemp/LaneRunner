# LaneRunner

**LaneRunner** is a Carla simulator-based game built with Pygame, designed to enhance situation awareness (SA) in Level 3 automated driving vehicles.

## Table of Contents

- [LaneRunner](#lanerunner)
  - [Table of Contents](#table-of-contents)
  - [Project Purpose](#project-purpose)
  - [Impact](#impact)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Technical Features](#technical-features)
  - [Folder Structure](#folder-structure)
  - [Makefile Commands](#makefile-commands)
  - [Troubleshooting](#troubleshooting)
  - [Credits](#credits)
  - [License](#license)

## Project Purpose

The goal of LaneRunner is to:
- **Enhance driver situation awareness (SA)** during long, automated drives.
- **Promote engagement** (not distraction) during extended periods of automated driving.
- **Reduce boredom and disengagement** by providing a supportive, non-intrusive game experience.
- **Reinforce SA** so drivers remain mentally prepared for takeover requests.

The game is projected onto the vehicle windshield, integrating real-world driving with interactive gameplay. Players use external input devices. The game automatically pauses and requests driver takeover when safety requires, ensuring real-world safety is always prioritized.

## Impact

- **Keeps drivers engaged** without distracting from the driving task.
- **Supports mental readiness** for manual control transitions.
- **Demonstrates a novel approach** to in-vehicle user experience and safety.

---

## Getting Started

### Prerequisites

- **Linux (Ubuntu 20.04 or later recommended)**
  - Python 3.7
  - pip (Python package manager)
  - make
  - git
  - NVIDIA GPU with latest drivers (for CARLA)

- **CARLA Simulator 0.9.14_RSS**  
  Only this version is supported and tested.

### Installation

1. **Clone this repository:**
   ```bash
   git clone <repository_url>
   cd LaneRunner
   ```

2. **Set up environment variables:**  
   The project uses an `environment.sh` file to configure the required environment variables for CARLA.  
   Open `environment.sh` in the project root and update the following lines with the correct paths for your system:

   ```bash
   export CARLA_ROOT="/path/to/your/CARLA_0.9.14_RSS"
   export PYTHONPATH="$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla/dist/carla-0.9.14-py3.7-linux-x86_64.egg"
   export PYTHONPATH="$PYTHONPATH:${CARLA_ROOT}/PythonAPI/carla"
   ```

   Replace `/path/to/your/CARLA_0.9.14_RSS` with the actual locations on your machine.

   Before running the project, you can activate these variables in your terminal:

   ```bash
   source environment.sh
   ```

   Note: The `make` commands in this project automatically source `environment.sh` for you, so manual activation is usually not required unless you are running scripts directly.

3. **Install and run:**
   ```bash
   make
   ```
   This will set up the Python environment, install dependencies, and start the CARLA server, and the LaneRunner client.

---

## Technical Features

- **CARLA Integration:** Real-time interaction with the CARLA simulator world.
- **Pygame UI:** Responsive, real-time rendering and input handling.
- **Gesture Controls:** Play using external devices for natural, intuitive interaction.
- **Coin Collection & Scoring:** Collect coins and track your score.
- **2D Map Rendering:** Top-down map view with hero, avatar, and objects.
- **Sound & Visual Feedback:** Custom sounds and images for immersive feedback.
- **Modular Structure:** Easily extend or modify actors, sensors, and visualizations.
- **Command-Line Configuration:** Adjust server, map, resolution, and more at launch.

---

## Folder Structure

```
session_logs/ # Session logs from User Experience study
logs/         # Log files for debugging
src/
  assets/      # Fonts, images, sounds
  core/        # Constants, colors, and shared logic
  data/        # Game state, avatar, coin, sound logic
  engine/      # CARLA world, sensors, map rendering
  sessions/    # Session management and logging
  utils/       # Utility functions
  views/       # Game view and rendering
lane_runner.py  # Starting point for the game
requirements.txt
environment.sh
Makefile
wheel_config.ini # Configuration for building the game with steering wheel
```

---

## Makefile Commands

The following `make` recipes are available to manage the project:

- **make** or **make run**: Installs dependencies and starts the full project (server, client, traffic).
- **make install**: Sets up the Python virtual environment and installs all dependencies.
- **make start**: Starts the CARLA server and client (includes traffic generation).
- **make server**: Starts only the CARLA server.
- **make client**: Runs the LaneRunner client.
- **make traffic**: Starts the CARLA traffic generator with 150 vehicles.
- **make stop**: Stops all running CARLA server, client, and traffic processes.
- **make stop-server**: Stops only the CARLA server process.
- **make stop-client**: Stops the client process.
- **make stop-traffic**: Stops only the CARLA traffic generator process.
- **make clean**: Stops all processes and removes virtual environment, cache, and PID files.
- **make clean-logs**: Removes all log files in the `logs/` directory.
- **make clear**: Runs both `clean` and `clean-logs` to fully reset the project state.
- **make push**: Pushes session logs changes to the remote repository (requires git).

---

## Troubleshooting

- If the game or CARLA server crashes, kill all CARLA processes and restart:
  ```bash
  make stop
  make start
  ```
- Check the logs in the `logs/` directory for error details.

---

## Credits

- Built with [CARLA Simulator](https://carla.org/)
- Pygame: [pygame.org](https://www.pygame.org/)

---

## License

- **Code:** MIT License (see [`LICENSE`](LICENSE) file)
- **Fonts:** 
  - Montserrat, licensed under the [SIL Open Font License 1.1](src/assets/fonts/Montserrat/OFL.txt)
  - Goldman, licensed under the [SIL Open Font License 1.1](src/assets/fonts/Goldman/OFL.txt)
- **Assets:** See `src/assets/` for individual licenses.

---

*For questions or issues, please open an issue or contact the project maintainers.*
