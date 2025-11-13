import csv
import os
import statistics
import uuid
import logging
import pygame

# Local imports
from src.utils.log_lanerunner_timestamp import log_lanerunner_timestamp
from src.core.colors import COLOR_SCARLET_RED_0, COLOR_WHITE

class LaneRunnerLogger:
    def __init__(self, filename='session_logs/lanerunner_log.csv'):
        self.filename = filename
        self.fields = [
            "session_id", "date_time",
            # TOR 1
            "tor1_time", "takeover1_time", "stab1_start", "stab1_end", "steer_values1", "stable1", "steer_mean1", "steer_std1",
            # TOR 2
            "tor2_time", "takeover2_time", "stab2_start", "stab2_end", "steer_values2", "stable2", "steer_mean2", "steer_std2"
        ]
        self.ensure_file_exists()
        self.reset_session()

    def ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=self.fields)
                writer.writeheader()

    def start_session(self):
        self.reset_session()
        self.session_id = str(uuid.uuid4())
        self.date_time = log_lanerunner_timestamp()
        logging.info(f"Session started with ID: {self.session_id} at {self.date_time}")

    def reset_session(self):
        self.session_id = None
        self.date_time = None
        self.tor_counter = 1
        # TOR 1
        self.tor1_time = None
        self.takeover1_time = None
        self.stab1_start = None
        self.stab1_end = None
        self.steer_values1 = []
        self.stable1 = None
        self.steer_mean1 = 0.0
        self.steer_std1 = 0.0
        # TOR 2
        self.tor2_time = None
        self.takeover2_time = None
        self.stab2_start = None
        self.stab2_end = None
        self.steer_values2 = []
        self.stable2 = None
        self.steer_mean2 = 0.0
        self.steer_std2 = 0.0
        logging.info("Session data reset.")

    def add_value(self, tor_time=None, takeover_time=None, stab_start=None, stab_end=None, steer_values=None):
        tor_index = self.tor_counter
        if tor_index > 2:
            logging.warning("Maximum of 2 TORs already recorded. Ignoring extra data.")
            return

        if tor_time is not None:
            setattr(self, f"tor{tor_index}_time", tor_time)
        if takeover_time is not None:
            setattr(self, f"takeover{tor_index}_time", takeover_time)
        if stab_start is not None:
            setattr(self, f"stab{tor_index}_start", stab_start)
        if stab_end is not None:
            setattr(self, f"stab{tor_index}_end", stab_end)
        if steer_values is not None:
            setattr(self, f"steer_values{tor_index}", steer_values)
            if steer_values:
                mean = statistics.mean(steer_values)
                std = statistics.stdev(steer_values) if len(steer_values) > 1 else 0.0
                setattr(self, f"steer_mean{tor_index}", mean)
                setattr(self, f"steer_std{tor_index}", std)

        # ✅ If we have a complete TOR (based on stab_end), then increment
        if getattr(self, f"stab{tor_index}_end") is not None and getattr(self, f"steer_values{tor_index}"):
            logging.info(f"Finished logging TOR {tor_index}. Moving to next.")
            self.tor_counter += 1

    def calculate_stability(self):
        if self.steer_values1:
            self.stable1 = all(abs(value) < 0.1 for value in self.steer_values1)
        if self.steer_values2:
            self.stable2 = all(abs(value) < 0.1 for value in self.steer_values2)
        logging.info("Stability calculated for steer values.")

    def calculate_statistics(self):
        if self.steer_values1:
            self.steer_mean1 = statistics.mean(self.steer_values1)
            self.steer_std1 = statistics.stdev(self.steer_values1) if len(self.steer_values1) > 1 else 0.0
        if self.steer_values2:
            self.steer_mean2 = statistics.mean(self.steer_values2)
            self.steer_std2 = statistics.stdev(self.steer_values2) if len(self.steer_values2) > 1 else 0.0
        logging.info("Statistics calculated for steer values.")

    def save_session(self):
        if not self.session_id:
            logging.error("No session started to save.")
            return

        self.calculate_stability()
        self.calculate_statistics()

        with open(self.filename, 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fields)
            row = {
                "session_id": self.session_id,
                "date_time": self.date_time,
                # TOR 1
                "tor1_time": self.tor1_time,
                "takeover1_time": self.takeover1_time,
                "stab1_start": self.stab1_start,
                "stab1_end": self.stab1_end,
                "steer_values1": ";".join(f"{v:.3f}" for v in self.steer_values1),
                "stable1": self.stable1,
                "steer_mean1": round(self.steer_mean1, 3),
                "steer_std1": round(self.steer_std1, 3),
                # TOR 2
                "tor2_time": self.tor2_time,
                "takeover2_time": self.takeover2_time,
                "stab2_start": self.stab2_start,
                "stab2_end": self.stab2_end,
                "steer_values2": ";".join(f"{v:.3f}" for v in self.steer_values2),
                "stable2": self.stable2,
                "steer_mean2": round(self.steer_mean2, 3),
                "steer_std2": round(self.steer_std2, 3),
            }
            writer.writerow(row)
        logging.info(f"Session {self.session_id} saved successfully.")
        self.reset_session()

    def render_recording_status(self, display):
        if not self.session_id:
            return

        dot_radius = 10
        dot_color = COLOR_SCARLET_RED_0
        text_color = COLOR_WHITE

        position = (display.get_width() - dot_radius - 20, display.get_height() - dot_radius - 40)
        # Draw red dot
        pygame.draw.circle(display, dot_color, position, dot_radius)

        # Render tor_counter as text
        font = pygame.font.SysFont(None, 16)
        text_surface = font.render(str(self.tor_counter), True, text_color)
        text_rect = text_surface.get_rect(center=position)
        display.blit(text_surface, text_rect)