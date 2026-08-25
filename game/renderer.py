"""Pygame rendering layer.

Pygame is imported lazily so headless training, evaluation, and unit tests work
on machines where only PyTorch/NumPy/Pillow are installed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from config import CAR_COLOURS
from game.environment import RacingEnv

try:  # pragma: no cover - exercised on a machine with Pygame installed
    import pygame
except ModuleNotFoundError:  # pragma: no cover - headless CI path
    pygame = None  # type: ignore[assignment]


WINDOW_WIDTH = 1320
WINDOW_HEIGHT = 720
TRACK_X = 20
TRACK_Y = 52
SIDEBAR_X = 1000
SIDEBAR_WIDTH = 300


class PygameUnavailableError(RuntimeError):
    pass


def require_pygame() -> Any:
    if pygame is None:
        raise PygameUnavailableError(
            "Pygame is not installed. Run 'python -m pip install -r requirements.txt' first."
        )
    return pygame


class PygameRenderer:
    def __init__(self) -> None:  # pragma: no cover - requires display
        pg = require_pygame()
        pg.init()
        pg.display.set_caption("CSE440 Self-Driving Car Racing Game")
        self.screen = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pg.time.Clock()
        self.font_small = pg.font.SysFont("Segoe UI", 17)
        self.font_body = pg.font.SysFont("Segoe UI", 20)
        self.font_button = pg.font.SysFont("Segoe UI Semibold", 23)
        self.font_heading = pg.font.SysFont("Segoe UI Semibold", 30)
        self.font_title = pg.font.SysFont("Segoe UI Semibold", 46)
        self.font_mono = pg.font.SysFont("Consolas", 18)
        self._track_surfaces: dict[str, Any] = {}

    def tick(self, fps: int = 60) -> float:  # pragma: no cover
        return self.clock.tick(fps) / 1000.0

    def present(self) -> None:  # pragma: no cover
        require_pygame().display.flip()

    def events(self) -> list[Any]:  # pragma: no cover
        return list(require_pygame().event.get())

    def draw_game(
        self,
        env: RacingEnv,
        *,
        mode_title: str,
        car_colour: str,
        stats: Mapping[str, object],
        controls: Iterable[str],
        status: str = "",
        show_sensors: bool = True,
        overlay: str | None = None,
    ) -> None:  # pragma: no cover
        pg = require_pygame()
        self.screen.fill((17, 23, 33))
        self._text(
            f"CSE440 • {mode_title}",
            (TRACK_X, 13),
            self.font_heading,
            (238, 242, 248),
        )

        track_surface = self._track_surface(env)
        self.screen.blit(track_surface, (TRACK_X, TRACK_Y))
        pg.draw.rect(
            self.screen,
            (105, 118, 136),
            (TRACK_X - 1, TRACK_Y - 1, env.track.width + 2, env.track.height + 2),
            width=1,
            border_radius=3,
        )

        if show_sensors and env.last_sensor_reading is not None:
            origin = self._world_to_screen(env.car.position)
            for endpoint, distance in zip(
                env.last_sensor_reading.endpoints,
                env.last_sensor_reading.distances,
                strict=True,
            ):
                end = self._world_to_screen(endpoint)
                ratio = float(distance / env.config.sensor_max_distance)
                colour = (255, 181, 62) if ratio < 0.40 else (86, 205, 255)
                pg.draw.aaline(self.screen, colour, origin, end)
                pg.draw.circle(self.screen, colour, end, 3)

        self._draw_car(env, car_colour)
        self._draw_sidebar(mode_title, stats, controls, status)

        if overlay:
            self._draw_overlay(overlay)

    def draw_menu(
        self,
        *,
        title: str,
        subtitle: str,
        options: list[str],
        selected_index: int,
        footer: str,
    ) -> list[Any]:  # pragma: no cover
        pg = require_pygame()
        self.screen.fill((15, 23, 34))
        self._draw_menu_background()
        self._text(title, (WINDOW_WIDTH // 2, 96), self.font_title, (244, 247, 252), center=True)
        self._text(subtitle, (WINDOW_WIDTH // 2, 155), self.font_body, (168, 181, 201), center=True)

        button_rects: list[Any] = []
        start_y = 220
        for index, label in enumerate(options):
            rect = pg.Rect(WINDOW_WIDTH // 2 - 210, start_y + index * 64, 420, 48)
            selected = index == selected_index
            fill = (47, 111, 196) if selected else (31, 43, 59)
            border = (112, 176, 255) if selected else (66, 82, 105)
            pg.draw.rect(self.screen, fill, rect, border_radius=10)
            pg.draw.rect(self.screen, border, rect, width=2, border_radius=10)
            self._text(label, rect.center, self.font_button, (249, 251, 255), center=True)
            button_rects.append(rect)

        self._text(footer, (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 36), self.font_small, (139, 154, 176), center=True)
        return button_rects

    def draw_settings(
        self,
        *,
        track: str,
        car_colour: str,
        training_episodes: int,
        selected_index: int,
    ) -> list[Any]:  # pragma: no cover
        options = [
            f"Track difficulty: {track.title()}",
            f"Car colour: {car_colour.title()}",
            f"Training episodes: {training_episodes}",
            "Back to main menu",
        ]
        return self.draw_menu(
            title="Settings",
            subtitle="Use Left/Right to change a selected value",
            options=options,
            selected_index=selected_index,
            footer="Arrow keys navigate • Enter selects • Esc returns",
        )

    def draw_message_screen(
        self,
        *,
        title: str,
        lines: Iterable[str],
        footer: str = "Press Esc or Enter to return",
    ) -> None:  # pragma: no cover
        self.screen.fill((15, 23, 34))
        self._draw_menu_background()
        self._text(title, (WINDOW_WIDTH // 2, 110), self.font_title, (244, 247, 252), center=True)
        y = 205
        for line in lines:
            self._text(str(line), (WINDOW_WIDTH // 2, y), self.font_body, (211, 219, 232), center=True)
            y += 38
        self._text(footer, (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40), self.font_small, (139, 154, 176), center=True)

    def _track_surface(self, env: RacingEnv) -> Any:  # pragma: no cover
        pg = require_pygame()
        key = env.track.name
        if key not in self._track_surfaces:
            image = env.track.display_image
            surface = pg.image.frombuffer(image.tobytes(), image.size, "RGB").copy().convert()
            self._track_surfaces[key] = surface
        return self._track_surfaces[key]

    def _draw_car(self, env: RacingEnv, car_colour: str) -> None:  # pragma: no cover
        pg = require_pygame()
        body_colour = CAR_COLOURS.get(car_colour, CAR_COLOURS["red"])
        corners = [self._world_to_screen(point) for point in env.car.corners()]
        shadow = [(x + 3, y + 4) for x, y in corners]
        pg.draw.polygon(self.screen, (18, 20, 24), shadow)
        pg.draw.polygon(self.screen, body_colour, corners)
        pg.draw.polygon(self.screen, (245, 248, 252), corners, width=2)

        # Windshield and front marker make the heading immediately readable.
        position = env.car.position
        heading = env.car.heading_vector
        normal = np.array([-heading[1], heading[0]], dtype=np.float32)
        windshield_center = position + heading * 4.0
        windshield = [
            windshield_center + heading * 4.0 + normal * 5.0,
            windshield_center + heading * 4.0 - normal * 5.0,
            windshield_center - heading * 3.0 - normal * 5.0,
            windshield_center - heading * 3.0 + normal * 5.0,
        ]
        pg.draw.polygon(
            self.screen,
            (126, 194, 229),
            [self._world_to_screen(point) for point in windshield],
        )
        nose = self._world_to_screen(position + heading * (env.config.car_length / 2.0 + 3.0))
        pg.draw.circle(self.screen, (255, 226, 106), nose, 3)

    def _draw_sidebar(
        self,
        mode_title: str,
        stats: Mapping[str, object],
        controls: Iterable[str],
        status: str,
    ) -> None:  # pragma: no cover
        pg = require_pygame()
        panel = pg.Rect(SIDEBAR_X, TRACK_Y, SIDEBAR_WIDTH, 640)
        pg.draw.rect(self.screen, (24, 33, 47), panel, border_radius=12)
        pg.draw.rect(self.screen, (61, 79, 104), panel, width=1, border_radius=12)
        self._text(mode_title, (SIDEBAR_X + 20, TRACK_Y + 20), self.font_heading, (240, 244, 250))

        y = TRACK_Y + 72
        for label, value in stats.items():
            self._text(str(label), (SIDEBAR_X + 20, y), self.font_small, (137, 154, 178))
            self._text(str(value), (SIDEBAR_X + 280, y), self.font_mono, (236, 241, 248), right=True)
            y += 33

        y = max(y + 14, TRACK_Y + 390)
        self._text("Controls", (SIDEBAR_X + 20, y), self.font_body, (219, 229, 243))
        y += 34
        for line in controls:
            self._text(str(line), (SIDEBAR_X + 20, y), self.font_small, (166, 181, 202))
            y += 25

        if status:
            status_rect = pg.Rect(SIDEBAR_X + 16, TRACK_Y + 566, SIDEBAR_WIDTH - 32, 56)
            pg.draw.rect(self.screen, (34, 50, 70), status_rect, border_radius=8)
            self._wrapped_text(status, status_rect.inflate(-16, -10), self.font_small, (199, 216, 239))

    def _draw_overlay(self, message: str) -> None:  # pragma: no cover
        pg = require_pygame()
        overlay = pg.Surface((520, 130), pg.SRCALPHA)
        overlay.fill((12, 18, 27, 225))
        rect = overlay.get_rect(center=(TRACK_X + 480, TRACK_Y + 320))
        self.screen.blit(overlay, rect)
        pg.draw.rect(self.screen, (111, 157, 220), rect, width=2, border_radius=12)
        self._text(message, rect.center, self.font_heading, (245, 248, 252), center=True)

    def _draw_menu_background(self) -> None:  # pragma: no cover
        pg = require_pygame()
        for index in range(12):
            inset = index * 24
            colour = (18 + index, 28 + index, 42 + index)
            pg.draw.ellipse(
                self.screen,
                colour,
                (-180 + inset, -100 + inset // 2, 700 - inset, 500 - inset // 2),
                width=2,
            )
        pg.draw.circle(self.screen, (25, 53, 82), (WINDOW_WIDTH - 130, 95), 220, width=2)
        pg.draw.circle(self.screen, (31, 68, 105), (WINDOW_WIDTH - 130, 95), 160, width=2)

    def _world_to_screen(self, point: np.ndarray | tuple[float, float]) -> tuple[int, int]:
        return int(round(float(point[0]) + TRACK_X)), int(round(float(point[1]) + TRACK_Y))

    def _text(
        self,
        text: str,
        position: tuple[int, int],
        font: Any,
        colour: tuple[int, int, int],
        *,
        center: bool = False,
        right: bool = False,
    ) -> None:  # pragma: no cover
        surface = font.render(text, True, colour)
        rect = surface.get_rect()
        if center:
            rect.center = position
        elif right:
            rect.topright = position
        else:
            rect.topleft = position
        self.screen.blit(surface, rect)

    def _wrapped_text(self, text: str, rect: Any, font: Any, colour: tuple[int, int, int]) -> None:  # pragma: no cover
        words = text.split()
        line = ""
        y = rect.top
        for word in words:
            candidate = f"{line} {word}".strip()
            if font.size(candidate)[0] <= rect.width:
                line = candidate
            else:
                self._text(line, (rect.left, y), font, colour)
                y += font.get_linesize()
                line = word
        if line:
            self._text(line, (rect.left, y), font, colour)
