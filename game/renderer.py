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


WINDOW_WIDTH = 1640
WINDOW_HEIGHT = 880
TRACK_X = 20
TRACK_Y = 52
SIDEBAR_X = 1320
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
        
        info = pg.display.Info()
        global WINDOW_WIDTH, WINDOW_HEIGHT, SIDEBAR_X
        # Fit the screen completely
        WINDOW_WIDTH = info.current_w
        WINDOW_HEIGHT = info.current_h
        # Ensure minimum size just in case
        WINDOW_WIDTH = max(1000, WINDOW_WIDTH)
        WINDOW_HEIGHT = max(600, WINDOW_HEIGHT)
        SIDEBAR_X = WINDOW_WIDTH - SIDEBAR_WIDTH - 20
        
        self.screen = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pg.FULLSCREEN)
        self.clock = pg.time.Clock()
        self.font_small = pg.font.SysFont("Segoe UI", 17)
        self.font_body = pg.font.SysFont("Segoe UI", 20)
        self.font_button = pg.font.SysFont("Segoe UI Semibold", 23)
        self.font_heading = pg.font.SysFont("Segoe UI Semibold", 30)
        self.font_title = pg.font.SysFont("Segoe UI Semibold", 46)
        self.font_mono = pg.font.SysFont("Consolas", 18)
        self._track_surfaces: dict[str, Any] = {}

    @property
    def track_width(self) -> int:
        return SIDEBAR_X - TRACK_X - 20
        
    @property
    def track_height(self) -> int:
        return WINDOW_HEIGHT - TRACK_Y - 20

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
        live_graph_data: tuple[str, list[float]] | None = None,
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
                
                # Techy color gradient based on distance
                if ratio < 0.3:
                    colour = (255, 50, 50)  # Danger Red
                elif ratio < 0.6:
                    colour = (255, 200, 50) # Warning Yellow
                else:
                    colour = (50, 255, 200) # Clear Cyan

                # Draw dashed line for the sensor beam
                # We can approximate a dashed line by drawing multiple small lines
                beam_vector = np.array([end[0] - origin[0], end[1] - origin[1]], dtype=np.float32)
                length = np.linalg.norm(beam_vector)
                if length > 0.1:
                    direction = beam_vector / length
                    dash_len = 8.0
                    gap_len = 6.0
                    curr = 0.0
                    while curr < length:
                        start_dash = origin + direction * curr
                        end_dash = origin + direction * min(curr + dash_len, length)
                        pg.draw.aaline(self.screen, colour, (int(start_dash[0]), int(start_dash[1])), (int(end_dash[0]), int(end_dash[1])))
                        curr += dash_len + gap_len

                # Draw tech crosshair at the impact point
                cx, cy = end
                s = 4 # crosshair size
                pg.draw.line(self.screen, colour, (cx - s, cy), (cx + s, cy), 2)
                pg.draw.line(self.screen, colour, (cx, cy - s), (cx, cy + s), 2)
                pg.draw.rect(self.screen, colour, (cx - s, cy - s, s * 2 + 1, s * 2 + 1), 1)

        if hasattr(env, "traffic"):
            for t_car in env.traffic:
                self._draw_car(t_car, "blue")

        self._draw_car(env.car, car_colour)
        self._draw_sidebar(mode_title, stats, controls, status, live_graph_data)

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

    def draw_evaluation_metrics(
        self,
        *,
        track: str,
        metadata: dict[str, Any],
        images: list[Any],
    ) -> None:  # pragma: no cover
        pg = require_pygame()
        self.screen.fill((15, 23, 34))
        self._draw_menu_background()
        self._text(f"AI Metrics for {track.title()}", (WINDOW_WIDTH // 2, 60), self.font_title, (244, 247, 252), center=True)
        self._text("Press Enter to begin evaluation • Esc to return", (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 40), self.font_small, (139, 154, 176), center=True)
        
        # Display hyperparameters
        config = metadata.get("training_config", {})
        info_x = 50
        info_y = 130
        self._text("Hyperparameters:", (info_x, info_y), self.font_heading, (244, 247, 252))
        info_y += 50
        keys_to_show = ["episodes", "learning_rate", "batch_size", "gamma", "epsilon_start", "epsilon_end", "hidden_size", "double_dqn"]
        for key in keys_to_show:
            val = config.get(key, "N/A")
            label = key.replace("_", " ").title()
            self._text(f"{label}:", (info_x, info_y), self.font_body, (139, 154, 176))
            self._text(str(val), (info_x + 180, info_y), self.font_mono, (236, 241, 248))
            info_y += 35
            
        # Draw images
        if not images:
            self._text("No graphs found. Train the AI to generate metrics.", (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2), self.font_heading, (255, 100, 100), center=True)
            return

        img_w = (WINDOW_WIDTH - 450) // 2
        img_spacing = 20
        
        x_offset = 400
        y_offset = 130
        
        for i, img in enumerate(images):
            scale_factor = img_w / img.get_width()
            new_h = int(img.get_height() * scale_factor)
            scaled_img = pg.transform.smoothscale(img, (img_w, new_h))
            
            row = i // 2
            col = i % 2
            
            px = x_offset + col * (img_w + img_spacing)
            py = y_offset + row * (new_h + img_spacing)
            
            border_rect = pg.Rect(px - 2, py - 2, img_w + 4, new_h + 4)
            pg.draw.rect(self.screen, (61, 79, 104), border_rect, border_radius=4)
            self.screen.blit(scaled_img, (px, py))

    def _track_surface(self, env: RacingEnv) -> Any:  # pragma: no cover
        pg = require_pygame()
        key = env.track.name
        if key not in self._track_surfaces:
            image = env.track.display_image
            surface = pg.image.frombuffer(image.tobytes(), image.size, "RGB").copy().convert()
            self._track_surfaces[key] = surface
        return self._track_surfaces[key]

    def _draw_car(self, car, car_colour: str) -> None:  # pragma: no cover
        pg = require_pygame()
        body_colour = CAR_COLOURS.get(car_colour, CAR_COLOURS["red"])
        position = car.position
        heading = car.heading_vector
        normal = np.array([-heading[1], heading[0]], dtype=np.float32)
        length = car.config.car_length
        width = car.config.car_width

        # Realistic sleek sports car body shape
        # Define relative points from center (-0.5 to 0.5 for length and width)
        # We will create a tapered front, wide fenders, and a spoiler
        body_points = [
            (0.5, 0.25),   # Front right nose
            (0.4, 0.45),   # Front right fender
            (0.1, 0.48),   # Mid right
            (-0.3, 0.5),   # Rear right fender
            (-0.5, 0.45),  # Rear right corner
            (-0.5, -0.45), # Rear left corner
            (-0.3, -0.5),  # Rear left fender
            (0.1, -0.48),  # Mid left
            (0.4, -0.45),  # Front left fender
            (0.5, -0.25),  # Front left nose
        ]
        
        # Transform points to world and screen coordinates
        def to_screen(rel_x, rel_y):
            pt = position + heading * (length * rel_x) + normal * (width * rel_y)
            return self._world_to_screen(pt)

        screen_body_points = [to_screen(rx, ry) for rx, ry in body_points]

        # Draw shadow
        shadow = [(x + 4, y + 5) for x, y in screen_body_points]
        pg.draw.polygon(self.screen, (18, 20, 24), shadow)

        # Draw wheels (dark grey, sticking out slightly)
        wheel_length = length * 0.2
        wheel_width = width * 0.2
        wheel_color = (25, 25, 25)
        
        fl_pos = position + heading * (length * 0.3) + normal * (width * 0.5)
        fr_pos = position + heading * (length * 0.3) - normal * (width * 0.5)
        bl_pos = position - heading * (length * 0.3) + normal * (width * 0.52)
        br_pos = position - heading * (length * 0.3) - normal * (width * 0.52)

        for w_pos in [fl_pos, fr_pos, bl_pos, br_pos]:
            w_corners = [
                self._world_to_screen(w_pos + heading * wheel_length/2 + normal * wheel_width/2),
                self._world_to_screen(w_pos + heading * wheel_length/2 - normal * wheel_width/2),
                self._world_to_screen(w_pos - heading * wheel_length/2 - normal * wheel_width/2),
                self._world_to_screen(w_pos - heading * wheel_length/2 + normal * wheel_width/2),
            ]
            pg.draw.polygon(self.screen, wheel_color, w_corners)

        # Draw main car body
        pg.draw.polygon(self.screen, body_colour, screen_body_points)
        # Highlight outline for 3D effect
        pg.draw.polygon(self.screen, (255, 255, 255), screen_body_points, width=1)

        # Cockpit/Windshield (swept back, dark tint)
        cockpit_points = [
            (0.2, 0.3),    # Front right
            (-0.25, 0.35), # Rear right
            (-0.35, 0.2),  # Back right
            (-0.35, -0.2), # Back left
            (-0.25, -0.35),# Rear left
            (0.2, -0.3),   # Front left
            (0.3, -0.15),  # Front center left
            (0.3, 0.15),   # Front center right
        ]
        screen_cockpit = [to_screen(rx, ry) for rx, ry in cockpit_points]
        pg.draw.polygon(self.screen, (20, 25, 30), screen_cockpit)
        
        # Add a light glare to the windshield
        glare_points = [(0.2, 0.2), (0.1, 0.25), (0.1, -0.25), (0.2, -0.2)]
        screen_glare = [to_screen(rx, ry) for rx, ry in glare_points]
        pg.draw.polygon(self.screen, (80, 100, 120), screen_glare)

        # Rear Spoiler
        spoiler_points = [
            (-0.45, 0.4),
            (-0.38, 0.4),
            (-0.38, -0.4),
            (-0.45, -0.4),
        ]
        screen_spoiler = [to_screen(rx, ry) for rx, ry in spoiler_points]
        pg.draw.polygon(self.screen, (30, 30, 30), screen_spoiler)
        
        # Headlights (techy glow)
        hl_fl = position + heading * (length * 0.45) + normal * (width * 0.35)
        hl_fr = position + heading * (length * 0.45) - normal * (width * 0.35)
        pg.draw.circle(self.screen, (255, 255, 255), self._world_to_screen(hl_fl), 3)
        pg.draw.circle(self.screen, (200, 230, 255), self._world_to_screen(hl_fl), 5, width=1)
        pg.draw.circle(self.screen, (255, 255, 255), self._world_to_screen(hl_fr), 3)
        pg.draw.circle(self.screen, (200, 230, 255), self._world_to_screen(hl_fr), 5, width=1)
        
        # Taillights
        tl_bl = position - heading * (length * 0.48) + normal * (width * 0.4)
        tl_br = position - heading * (length * 0.48) - normal * (width * 0.4)
        pg.draw.rect(self.screen, (255, 50, 50), (*self._world_to_screen(tl_bl), 3, 3))
        pg.draw.rect(self.screen, (255, 50, 50), (*self._world_to_screen(tl_br), 3, 3))

    def _draw_sidebar(
        self,
        mode_title: str,
        stats: Mapping[str, object],
        controls: Iterable[str],
        status: str,
        live_graph_data: tuple[str, list[float]] | None = None,
    ) -> None:  # pragma: no cover
        pg = require_pygame()
        panel_height = WINDOW_HEIGHT - TRACK_Y - 20
        panel = pg.Rect(SIDEBAR_X, TRACK_Y, SIDEBAR_WIDTH, panel_height)
        pg.draw.rect(self.screen, (24, 33, 47), panel, border_radius=12)
        pg.draw.rect(self.screen, (61, 79, 104), panel, width=1, border_radius=12)
        self._text(mode_title, (SIDEBAR_X + 20, TRACK_Y + 20), self.font_heading, (240, 244, 250))

        y = TRACK_Y + 72
        for label, value in stats.items():
            self._text(str(label), (SIDEBAR_X + 20, y), self.font_small, (137, 154, 178))
            self._text(str(value), (SIDEBAR_X + 280, y), self.font_mono, (236, 241, 248), right=True)
            y += 33

        if live_graph_data and live_graph_data[1]:
            title, points = live_graph_data
            if len(points) > 1:
                graph_rect = pg.Rect(SIDEBAR_X + 20, y + 5, SIDEBAR_WIDTH - 40, 110)
                self._text(title, (graph_rect.left, graph_rect.top), self.font_small, (137, 154, 178))
                
                chart_rect = pg.Rect(graph_rect.left, graph_rect.top + 25, graph_rect.width, graph_rect.height - 25)
                pg.draw.rect(self.screen, (34, 50, 70), chart_rect, border_radius=4)
                
                min_val = min(points)
                max_val = max(points)
                range_val = max_val - min_val if max_val != min_val else 1.0
                
                step_x = chart_rect.width / (len(points) - 1)
                
                screen_points = []
                for i, val in enumerate(points):
                    norm = (val - min_val) / range_val
                    px = chart_rect.left + i * step_x
                    py = chart_rect.bottom - 4 - norm * (chart_rect.height - 8)
                    screen_points.append((px, py))
                    
                pg.draw.lines(self.screen, (111, 157, 220), False, screen_points, 2)
                y = graph_rect.bottom + 10

        y = max(y + 14, TRACK_Y + panel_height - 250)
        self._text("Controls", (SIDEBAR_X + 20, y), self.font_body, (219, 229, 243))
        y += 34
        for line in controls:
            self._text(str(line), (SIDEBAR_X + 20, y), self.font_small, (166, 181, 202))
            y += 25

        if status:
            status_rect = pg.Rect(SIDEBAR_X + 16, TRACK_Y + panel_height - 74, SIDEBAR_WIDTH - 32, 56)
            pg.draw.rect(self.screen, (34, 50, 70), status_rect, border_radius=8)
            self._wrapped_text(status, status_rect.inflate(-16, -10), self.font_small, (199, 216, 239))

    def _draw_overlay(self, message: str) -> None:  # pragma: no cover
        pg = require_pygame()
        overlay = pg.Surface((520, 130), pg.SRCALPHA)
        overlay.fill((12, 18, 27, 225))
        rect = overlay.get_rect(center=(TRACK_X + (SIDEBAR_X - TRACK_X)//2, TRACK_Y + (WINDOW_HEIGHT - TRACK_Y)//2))
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
