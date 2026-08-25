"""Interactive Pygame application for manual play, training, and evaluation."""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai.agent import DQNAgent
from ai.live_trainer import LiveTrainer
from ai.trainer import evaluate_agent
from config import CAR_COLOURS, MODELS_DIR, RESULTS_DIR, TRACK_CHOICES, SimulationConfig, TrainingConfig
from game.environment import RacingEnv
from game.renderer import PygameRenderer, require_pygame

LOGGER = logging.getLogger(__name__)


class SelfDrivingCarApp:
    MENU_OPTIONS = (
        "Manual Drive",
        "Train AI (DQN)",
        "Watch Trained AI",
        "Evaluate Trained AI",
        "Settings",
        "Quit",
    )
    TRAINING_EPISODE_CHOICES = (100, 300, 500, 1_000)
    SPEED_CHOICES = (1, 4, 16, 64, 128)

    def __init__(self) -> None:  # pragma: no cover - requires Pygame
        self.pg = require_pygame()
        self.renderer = PygameRenderer()
        self.running = True
        self.mode = "menu"
        self.menu_index = 0
        self.settings_index = 0
        self.track_index = 0
        self.colour_index = 0
        self.training_episode_index = 2
        self.speed_index = 2
        self.show_sensors = True
        self.env: RacingEnv | None = None
        self.agent: DQNAgent | None = None
        self.live_trainer: LiveTrainer | None = None
        self.manual_finished = False
        self.watch_finished = False
        self.status_message = ""
        self.shutdown_error: str | None = None
        self.message_title = ""
        self.message_lines: list[str] = []
        self._click_rects: list[Any] = []
        self.pg.key.set_repeat(250, 80)

    @property
    def selected_track(self) -> str:
        return TRACK_CHOICES[self.track_index]

    @property
    def selected_colour(self) -> str:
        return tuple(CAR_COLOURS)[self.colour_index]

    @property
    def selected_training_episodes(self) -> int:
        return self.TRAINING_EPISODE_CHOICES[self.training_episode_index]

    def run(self) -> int:  # pragma: no cover - requires Pygame
        while self.running:
            events = self.renderer.events()
            for event in events:
                if event.type == self.pg.QUIT:
                    self._shutdown()
                    break

            if not self.running:
                break

            if self.mode == "menu":
                self._menu(events)
            elif self.mode == "settings":
                self._settings(events)
            elif self.mode == "manual":
                self._manual(events)
            elif self.mode == "training":
                self._training(events)
            elif self.mode == "watch":
                self._watch(events)
            elif self.mode == "message":
                self._message(events)
            else:
                raise RuntimeError(f"Unknown app mode: {self.mode}")

            self.renderer.present()
            self.renderer.tick(60)

        self.pg.quit()
        return 0

    def _menu(self, events: list[Any]) -> None:
        for event in events:
            if event.type == self.pg.KEYDOWN:
                if event.key in (self.pg.K_UP, self.pg.K_w):
                    self.menu_index = (self.menu_index - 1) % len(self.MENU_OPTIONS)
                elif event.key in (self.pg.K_DOWN, self.pg.K_s):
                    self.menu_index = (self.menu_index + 1) % len(self.MENU_OPTIONS)
                elif event.key in (self.pg.K_RETURN, self.pg.K_SPACE):
                    self._activate_menu_option(self.menu_index)
                elif event.key == self.pg.K_ESCAPE:
                    self._shutdown()
            elif event.type == self.pg.MOUSEMOTION:
                self._select_rect_under_mouse(event.pos, is_settings=False)
            elif event.type == self.pg.MOUSEBUTTONDOWN and event.button == 1:
                index = self._rect_index_at(event.pos)
                if index is not None:
                    self.menu_index = index
                    self._activate_menu_option(index)

        if self.mode == "menu":
            self._click_rects = self.renderer.draw_menu(
                title="Self-Driving Car Racing Game",
                subtitle="Deep Q-Network reinforcement learning • CSE440",
                options=list(self.MENU_OPTIONS),
                selected_index=self.menu_index,
                footer="Arrow keys or mouse to navigate • Enter to select",
            )

    def _activate_menu_option(self, index: int) -> None:
        if index == 0:
            self._start_manual()
        elif index == 1:
            self._start_training()
        elif index == 2:
            self._start_watch()
        elif index == 3:
            self._run_evaluation()
        elif index == 4:
            self.mode = "settings"
            self.settings_index = 0
        elif index == 5:
            self._shutdown()

    def _settings(self, events: list[Any]) -> None:
        for event in events:
            if event.type == self.pg.KEYDOWN:
                if event.key == self.pg.K_UP:
                    self.settings_index = (self.settings_index - 1) % 4
                elif event.key == self.pg.K_DOWN:
                    self.settings_index = (self.settings_index + 1) % 4
                elif event.key in (self.pg.K_LEFT, self.pg.K_RIGHT):
                    direction = -1 if event.key == self.pg.K_LEFT else 1
                    self._change_setting(direction)
                elif event.key in (self.pg.K_RETURN, self.pg.K_SPACE):
                    if self.settings_index == 3:
                        self.mode = "menu"
                    else:
                        self._change_setting(1)
                elif event.key == self.pg.K_ESCAPE:
                    self.mode = "menu"
            elif event.type == self.pg.MOUSEMOTION:
                self._select_rect_under_mouse(event.pos, is_settings=True)
            elif event.type == self.pg.MOUSEBUTTONDOWN and event.button == 1:
                index = self._rect_index_at(event.pos)
                if index is not None:
                    self.settings_index = index
                    if index == 3:
                        self.mode = "menu"
                    else:
                        self._change_setting(1)

        if self.mode == "settings":
            self._click_rects = self.renderer.draw_settings(
                track=self.selected_track,
                car_colour=self.selected_colour,
                training_episodes=self.selected_training_episodes,
                selected_index=self.settings_index,
            )

    def _change_setting(self, direction: int) -> None:
        if self.settings_index == 0:
            self.track_index = (self.track_index + direction) % len(TRACK_CHOICES)
        elif self.settings_index == 1:
            self.colour_index = (self.colour_index + direction) % len(CAR_COLOURS)
        elif self.settings_index == 2:
            self.training_episode_index = (
                self.training_episode_index + direction
            ) % len(self.TRAINING_EPISODE_CHOICES)

    def _start_manual(self) -> None:
        config = replace(
            SimulationConfig(),
            max_steps=1_000_000,
            stuck_step_limit=1_000_000,
            target_laps=999,
        )
        self.env = RacingEnv(
            self.selected_track,
            simulation_config=config,
            terminate_on_lap=False,
        )
        self.manual_finished = False
        self.status_message = "Use the arrow keys to drive. Complete laps without leaving the road."
        self.mode = "manual"

    def _manual(self, events: list[Any]) -> None:
        assert self.env is not None
        for event in events:
            if event.type == self.pg.KEYDOWN:
                if event.key == self.pg.K_ESCAPE:
                    self.mode = "menu"
                    return
                if event.key == self.pg.K_r:
                    self.env.reset()
                    self.manual_finished = False
                    self.status_message = "Car reset."
                elif event.key == self.pg.K_g:
                    self.show_sensors = not self.show_sensors

        if not self.manual_finished:
            pressed = self.pg.key.get_pressed()
            throttle = 1.0 if pressed[self.pg.K_UP] else 0.0
            brake = 1.0 if pressed[self.pg.K_DOWN] else 0.0
            steering = float(pressed[self.pg.K_RIGHT]) - float(pressed[self.pg.K_LEFT])
            _, _, terminated, truncated, info = self.env.step_controls(
                throttle=throttle,
                brake=brake,
                steering=steering,
            )
            if info["lap_completed"]:
                self.status_message = f"Lap {self.env.lap_count} completed. Keep going!"
            if terminated or truncated:
                self.manual_finished = True
                self.status_message = "Collision. Press R to restart."

        overlay = "COLLISION — PRESS R" if self.manual_finished else None
        self.renderer.draw_game(
            self.env,
            mode_title="Manual Drive",
            car_colour=self.selected_colour,
            stats={
                "Track": self.selected_track.title(),
                "Reward": f"{self.env.episode_reward:.0f}",
                "Lap": self.env.lap_count,
                "Speed": f"{self.env.car.speed:.2f}",
                "Progress": f"{max(0.0, self.env.unwrapped_progress / self.env.track.point_count * 100):.1f}%",
                "Sensors": "On" if self.show_sensors else "Off",
            },
            controls=(
                "↑ accelerate   ↓ brake",
                "← / → steer",
                "R reset car",
                "G sensor rays",
                "Esc main menu",
            ),
            status=self.status_message,
            show_sensors=self.show_sensors,
            overlay=overlay,
        )

    def _start_training(self) -> None:
        self.env = RacingEnv(self.selected_track)
        config = TrainingConfig(episodes=self.selected_training_episodes)
        self.agent = DQNAgent(self.env.state_size, self.env.action_size, config)
        self.live_trainer = LiveTrainer(
            self.env,
            self.agent,
            total_episodes=self.selected_training_episodes,
            training_config=config,
        )
        self.status_message = "Training started. The epsilon value will decrease as the agent learns."
        self.mode = "training"

    def _training(self, events: list[Any]) -> None:
        assert self.env is not None and self.agent is not None and self.live_trainer is not None
        for event in events:
            if event.type == self.pg.KEYDOWN:
                if event.key == self.pg.K_ESCAPE:
                    self.live_trainer.save_now()
                    self.mode = "menu"
                    return
                if event.key == self.pg.K_SPACE:
                    self.live_trainer.toggle_pause()
                elif event.key == self.pg.K_s:
                    path = self.live_trainer.save_now()
                    self.status_message = f"Saved {path.name}"
                elif event.key == self.pg.K_g:
                    self.show_sensors = not self.show_sensors
                elif event.key in (self.pg.K_EQUALS, self.pg.K_PLUS, self.pg.K_KP_PLUS):
                    self.speed_index = min(self.speed_index + 1, len(self.SPEED_CHOICES) - 1)
                elif event.key in (self.pg.K_MINUS, self.pg.K_KP_MINUS):
                    self.speed_index = max(self.speed_index - 1, 0)

        steps_per_frame = self.SPEED_CHOICES[self.speed_index]
        status = self.live_trainer.step_many(steps_per_frame)
        if status.last_episode is not None:
            result = "lap completed" if status.last_episode.completed else status.last_episode.termination_reason
            self.status_message = (
                f"Episode {status.last_episode.episode}: reward {status.last_episode.reward:.0f}, "
                f"{result}. Results: {self.live_trainer.run_dir.name}"
            )

        if status.finished:
            overlay = "TRAINING COMPLETE"
        elif status.paused:
            overlay = "PAUSED"
        else:
            overlay = None

        self.renderer.draw_game(
            self.env,
            mode_title="DQN Training",
            car_colour=self.selected_colour,
            stats={
                "Track": self.selected_track.title(),
                "Episode": f"{status.episode}/{self.selected_training_episodes}",
                "Reward": f"{status.episode_reward:.0f}",
                "Steps": status.episode_steps,
                "Lap": self.env.lap_count,
                "Speed": f"{self.env.car.speed:.2f}",
                "Epsilon": f"{status.epsilon:.3f}",
                "Loss": "—" if status.loss is None else f"{status.loss:.4f}",
                "Sim speed": f"{steps_per_frame}x",
            },
            controls=(
                "Space pause / continue",
                "+ / − training speed",
                "S save model",
                "G sensor rays",
                "Esc save and exit",
            ),
            status=self.status_message,
            show_sensors=self.show_sensors,
            overlay=overlay,
        )

    def _model_path_for_selected_track(self) -> Path | None:
        best = MODELS_DIR / f"{self.selected_track}_best.pth"
        latest = MODELS_DIR / f"{self.selected_track}_latest.pth"
        if best.exists():
            return best
        if latest.exists():
            return latest
        return None

    def _start_watch(self) -> None:
        path = self._model_path_for_selected_track()
        if path is None:
            self._show_message(
                "No Trained Model",
                [
                    f"No model exists for the {self.selected_track.title()} track.",
                    "Choose Train AI first. This release includes validated best checkpoints for Easy, Medium, and Hard.",
                ],
            )
            return
        try:
            self.agent, metadata = DQNAgent.from_checkpoint(path, device="cpu")
            config = replace(
                SimulationConfig(),
                max_steps=1_000_000,
                stuck_step_limit=1_000_000,
                target_laps=999,
            )
            self.env = RacingEnv(
                self.selected_track,
                simulation_config=config,
                terminate_on_lap=False,
            )
            self.watch_finished = False
            trained_episode = metadata.get("episode", "unknown")
            self.status_message = f"Loaded {path.name} (training episode {trained_episode})."
            self.mode = "watch"
        except Exception as exc:  # display a recoverable error instead of closing the app
            self._show_message("Could Not Load Model", [type(exc).__name__, str(exc)])

    def _watch(self, events: list[Any]) -> None:
        assert self.env is not None and self.agent is not None
        for event in events:
            if event.type == self.pg.KEYDOWN:
                if event.key == self.pg.K_ESCAPE:
                    self.mode = "menu"
                    return
                if event.key == self.pg.K_r:
                    self.env.reset()
                    self.watch_finished = False
                    self.status_message = "AI car reset."
                elif event.key == self.pg.K_g:
                    self.show_sensors = not self.show_sensors

        if not self.watch_finished:
            state = self.env._get_state()  # latest observation after render/reset
            action = self.agent.select_action(state, evaluate=True)
            _, _, terminated, truncated, info = self.env.step(action)
            if info["lap_completed"]:
                self.status_message = f"AI completed lap {self.env.lap_count}."
            if terminated or truncated:
                self.watch_finished = True
                self.status_message = "AI collided. Press R to restart."

        overlay = "AI COLLISION — PRESS R" if self.watch_finished else None
        self.renderer.draw_game(
            self.env,
            mode_title="Watch Trained AI",
            car_colour=self.selected_colour,
            stats={
                "Track": self.selected_track.title(),
                "Reward": f"{self.env.episode_reward:.0f}",
                "Lap": self.env.lap_count,
                "Speed": f"{self.env.car.speed:.2f}",
                "Progress": f"{max(0.0, self.env.unwrapped_progress / self.env.track.point_count * 100):.1f}%",
                "Policy": "Greedy (ε = 0)",
                "Sensors": "On" if self.show_sensors else "Off",
            },
            controls=(
                "R reset AI car",
                "G sensor rays",
                "Esc main menu",
            ),
            status=self.status_message,
            show_sensors=self.show_sensors,
            overlay=overlay,
        )

    def _run_evaluation(self) -> None:
        path = self._model_path_for_selected_track()
        if path is None:
            self._show_message(
                "No Trained Model",
                [
                    f"No model exists for the {self.selected_track.title()} track.",
                    "Train a model first, then return to evaluation.",
                ],
            )
            return
        try:
            agent, metadata = DQNAgent.from_checkpoint(path, device="cpu")
            env = RacingEnv(self.selected_track)
            summary = evaluate_agent(env, agent, episodes=20, verbose=False)
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            result_path = RESULTS_DIR / f"evaluation_{self.selected_track}_{timestamp}.json"
            with result_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "model": str(path),
                        "metadata": metadata,
                        "summary": summary,
                    },
                    handle,
                    indent=2,
                )
                handle.write("\n")
            lap_steps = summary["mean_lap_steps"]
            lap_text = "No completed laps" if lap_steps is None else f"{lap_steps / 60.0:.2f} seconds"
            self._show_message(
                "Evaluation Complete",
                [
                    f"Model: {path.name}",
                    f"Track: {self.selected_track.title()}",
                    f"Success rate: {summary['success_rate'] * 100:.1f}% (20 episodes)",
                    f"Mean reward: {summary['mean_reward']:.1f}",
                    f"Mean completed lap time: {lap_text}",
                    f"Total collisions: {summary['total_collisions']}",
                    f"Saved: {result_path.name}",
                ],
            )
        except Exception as exc:
            self._show_message("Evaluation Failed", [type(exc).__name__, str(exc)])

    def _show_message(self, title: str, lines: list[str]) -> None:
        self.message_title = title
        self.message_lines = lines
        self.mode = "message"

    def _message(self, events: list[Any]) -> None:
        for event in events:
            if event.type == self.pg.KEYDOWN and event.key in (
                self.pg.K_ESCAPE,
                self.pg.K_RETURN,
                self.pg.K_SPACE,
            ):
                self.mode = "menu"
        self.renderer.draw_message_screen(title=self.message_title, lines=self.message_lines)

    def _rect_index_at(self, position: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self._click_rects):
            if rect.collidepoint(position):
                return index
        return None

    def _select_rect_under_mouse(self, position: tuple[int, int], *, is_settings: bool) -> None:
        index = self._rect_index_at(position)
        if index is not None:
            if is_settings:
                self.settings_index = index
            else:
                self.menu_index = index

    def _shutdown(self) -> None:
        if self.live_trainer is not None and self.mode == "training":
            try:
                self.live_trainer.save_now()
            except Exception as exc:
                self.shutdown_error = f"{type(exc).__name__}: {exc}"
                LOGGER.exception("Failed to save the live-training checkpoint during shutdown")
        self.running = False


def launch_gui() -> int:  # pragma: no cover - requires Pygame
    return SelfDrivingCarApp().run()
