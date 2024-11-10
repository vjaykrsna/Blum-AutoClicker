import asyncio
import os
import random
import time
import math
from itertools import product
import keyboard
import mouse
import pyautogui

from core.clicker.misc import Utilities
from core.logger.logger import logger
from core.localization.localization import get_language
from core.config.config import get_config_value
from typing import Tuple, Any

class BlumClicker:
    def __init__(self):
        # Initialize utility instance, pause state, window options, and replay count
        self.utils = Utilities()
        self.paused: bool = True
        self.window_options: str | None = None
        self.replays: int = 0

    async def handle_input(self) -> bool:
        # Handle user input for starting and toggling pause state
        if keyboard.is_pressed(get_config_value("START_HOTKEY")) and self.paused:
            self.paused = False
            logger.info(get_language("PRESS_P_TO_PAUSE"))
            await asyncio.sleep(0.2)  # Small delay to prevent rapid toggling
        elif keyboard.is_pressed(get_config_value("TOGGLE_HOTKEY")):
            self.paused = not self.paused
            logger.info(
                get_language("PROGRAM_PAUSED") if self.paused else get_language("PROGRAM_RESUMED")
            )
            await asyncio.sleep(0.2)  # Prevent rapid toggling
        return self.paused

    @staticmethod
    async def collect_green(screen: Any, rect: Tuple[int, int, int, int], side: str) -> bool:
        # Collect green tokens on the specified screen side
        width, height = screen.size
        x_start = 0 if side == "left" else width // 2
        x_end = width // 2 if side == "left" else width
        y_range = range(int(height * 0.25), height, 20)

        # Occasionally include upper area pixels for a broader search
        if random.random() < 0.03:
            y_range = range(0, int(height * 0.25), 20)

        bomb_positions = []  # Track bomb positions to avoid

        # Check pixels in the defined range for green tokens or bombs
        for x, y in product(range(x_start, x_end, 20), y_range):
            r, g, b = screen.getpixel((x, y))
            greenish_range = (100 <= r <= 180) and (210 <= g <= 255) and (b < 100)
            bomb_range = (100 <= r <= 150) and (100 <= g <= 150) and (100 <= b <= 150)

            if bomb_range:
                bomb_positions.append((x, y))
                continue  # Skip if a bomb is detected
            
            # If green token found and it's not near a bomb, click it
            if greenish_range and not BlumClicker.is_near_bomb(x, y, bomb_positions, 30):
                screen_x = rect[0] + x
                screen_y = rect[1] + y
                mouse.move(screen_x, screen_y, absolute=True)
                mouse.click(button=mouse.LEFT)
                
                # Randomized delay to mimic human behavior
                await asyncio.sleep(random.uniform(0.04, 0.08))
                return True
        return False

    @staticmethod
    async def collect_freeze(screen: Any, rect: Tuple[int, int, int, int], side: str) -> bool:
        # Collect freeze tokens with a probability of 15%
        if random.random() < 0.15:
            width, height = screen.size
            x_start = 0 if side == "left" else width // 2
            x_end = width // 2 if side == "left" else width
            y_range = range(int(height * 0.25), height, 20)

            bomb_positions = []  # Track bomb positions to avoid

            # Check pixels in the defined range for freeze tokens or bombs
            for x, y in product(range(x_start, x_end, 20), y_range):
                r, g, b = screen.getpixel((x, y))
                freeze_range = (50 <= r <= 100) and (150 <= g <= 200) and (210 <= b <= 255)
                bomb_range = (100 <= r <= 150) and (100 <= g <= 150) and (100 <= b <= 150)

                if bomb_range:
                    bomb_positions.append((x, y))
                    continue  # Skip if a bomb is detected
                
                # If freeze token found and it's not near a bomb, click it
                if freeze_range and not BlumClicker.is_near_bomb(x, y, bomb_positions, 30):
                    screen_x = rect[0] + x
                    screen_y = rect[1] + y
                    mouse.move(screen_x, screen_y, absolute=True)
                    mouse.click(button=mouse.LEFT)
                    return True
        return False

    @staticmethod
    def is_near_bomb(x: int, y: int, bomb_positions: list, radius: int) -> bool:
        # Check if a given point is near any bomb in a specified radius
        return any(math.hypot(bx - x, by - y) < radius for bx, by in bomb_positions)

    @staticmethod
    def detect_reload_screen(screen: Any) -> bool:
        # Detect if the reload screen is active and perform a reload action
        width, height = screen.size
        x1, y1 = (math.ceil(width * 0.43781), math.ceil(height * 0.60252))
        x2, y2 = (math.ceil(width * 0.24626), math.ceil(height * 0.429775))

        reload_button = screen.getpixel((x1, y1))
        white_pixel = screen.getpixel((x2, y2))

        # Reload screen if specific pixel colors match expected values
        if reload_button == (40, 40, 40) and white_pixel == (255, 255, 255):
            time.sleep(0.5)
            keyboard.press_and_release('F5')
            return True
        return False

    def detect_replay(self, screen: Any, rect: Tuple[int, int, int, int]) -> bool:
        # Detect replay button and handle replay actions with delay and limit
        max_replays = get_config_value("REPLAYS")
        replay_delay = get_config_value("REPLAY_DELAY")
        screen_x = rect[0] + int(screen.size[0] * 0.3075)
        screen_y = rect[1] + int(screen.size[1] * 0.87)
        color = pyautogui.pixel(screen_x, screen_y)

        if color != (255, 255, 255):
            return False
        if self.replays >= max_replays:
            logger.error(get_language("REPLAY_LIMIT_REACHED").format(replays=max_replays))
            os._exit(0)

        # Log and handle replay action
        logger.debug(f"Detected the replay button. Remaining replays: {max_replays - self.replays}")
        time.sleep(random.randint(replay_delay, replay_delay + 3) + random.random())
        mouse.move(screen_x + random.randint(1, 10), screen_y + random.randint(1, 10), absolute=True)
        mouse.click(button=mouse.LEFT)
        time.sleep(1)
        self.replays += 1
        return True

    async def run(self) -> None:
        # Main loop to run the clicker, manage screenshots, and handle user input
        try:
            window = self.utils.get_window()
            if not window:
                return logger.error(get_language("WINDOW_NOT_FOUND"))
            logger.info(get_language("CLICKER_INITIALIZED"))
            logger.info(get_language("FOUND_WINDOW").format(window=window.title))
            logger.info(get_language("PRESS_S_TO_START"))

            while True:
                if await self.handle_input():
                    continue
                rect = self.utils.get_rect(window)
                screenshot = self.utils.capture_screenshot(rect)

                # Collect tokens and handle replay/reload within an asyncio gather
                await asyncio.gather(
                    self.collect_green(screenshot, rect, "left"),
                    self.collect_green(screenshot, rect, "right"),
                    self.collect_freeze(screenshot, rect, "left"),
                    self.collect_freeze(screenshot, rect, "right")
                )
                self.detect_replay(screenshot, rect)
                self.detect_reload_screen(screenshot)

        except (Exception, ExceptionGroup) as error:
            logger.error(get_language("WINDOW_CLOSED").format(error=error))
