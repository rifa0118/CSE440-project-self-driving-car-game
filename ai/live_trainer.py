"""Non-blocking DQN training controller for the Pygame interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

from ai.agent import DQNAgent
from ai.trainer import create_run_directory
from config import MODELS_DIR, TrainingConfig
from game.environment import RacingEnv
from utils.metrics import EpisodeMetrics, MetricsStore


@dataclass(slots=True)
class LiveTrainingStatus:
    episode: int
    episode_reward: float
    episode_steps: int
    epsilon: float
    loss: float | None
    completed_episodes: int
    last_episode: EpisodeMetrics | None
    paused: bool
    finished: bool


class LiveTrainer:
    """Runs a bounded number of simulation steps per rendered frame."""

    def __init__(
        self,
        env: RacingEnv,
        agent: DQNAgent,
        *,
        total_episodes: int = 500,
        training_config: TrainingConfig | None = None,
        model_dir: str | Path = MODELS_DIR,
    ) -> None:
        if total_episodes <= 0:
            raise ValueError("total_episodes must be positive")
        self.env = env
        self.agent = agent
        self.config = training_config or agent.config
        self.total_episodes = int(total_episodes)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir = create_run_directory(env.track.name)
        self.metrics = MetricsStore(self.run_dir)
        self.best_model_path = self.model_dir / f"{env.track.name}_best.pth"
        self.latest_model_path = self.model_dir / f"{env.track.name}_latest.pth"
        self.best_score: tuple[int, float] = (-1, float("-inf"))
        self.paused = False
        self.finished = False
        self.episode_number = 1
        self.completed_episodes = 0
        self.last_episode: EpisodeMetrics | None = None
        self.current_losses: list[float] = []
        self.state = self.env.reset(seed=self.config.seed + self.episode_number)
        self.last_info: dict[str, Any] = {}

    def toggle_pause(self) -> None:
        if not self.finished:
            self.paused = not self.paused

    def step_many(self, count: int) -> LiveTrainingStatus:
        if count <= 0:
            return self.status()
        if self.paused or self.finished:
            return self.status()

        for _ in range(count):
            action = self.agent.select_action(self.state)
            next_state, reward, terminated, truncated, info = self.env.step(action)
            loss = self.agent.observe(
                self.state,
                action,
                reward,
                next_state,
                terminated or truncated,
            )
            if loss is not None:
                self.current_losses.append(loss)
            self.state = next_state
            self.last_info = info

            if terminated or truncated:
                self._finish_episode(info)
                if self.finished:
                    break
                self.episode_number += 1
                self.current_losses = []
                self.state = self.env.reset(seed=self.config.seed + self.episode_number)
                self.last_info = {}

        return self.status()

    def _finish_episode(self, info: dict[str, Any]) -> None:
        metrics = EpisodeMetrics(
            episode=self.episode_number,
            reward=self.env.episode_reward,
            steps=self.env.steps,
            laps=self.env.lap_count,
            lap_time_steps=self.env.steps if self.env.lap_count > 0 else None,
            collisions=self.env.collision_count,
            completed=self.env.lap_count > 0,
            epsilon=self.agent.epsilon,
            mean_loss=mean(self.current_losses) if self.current_losses else None,
            termination_reason=info.get("termination_reason"),
        )
        self.last_episode = metrics
        self.completed_episodes += 1
        self.metrics.append(metrics)
        self.metrics.save()

        metadata = {
            "track": self.env.track.name,
            "episode": metrics.episode,
            "episode_reward": metrics.reward,
            "completed": metrics.completed,
            "run_dir": str(self.run_dir),
            "source": "pygame_live_training",
        }
        score = (int(metrics.completed), metrics.reward)
        if score > self.best_score:
            self.best_score = score
            self.agent.save(self.best_model_path, metadata=metadata)

        if (
            metrics.episode % self.config.checkpoint_every_episodes == 0
            or metrics.episode == 1
        ):
            self.agent.save(self.latest_model_path, metadata=metadata)
        if metrics.episode % self.config.plot_every_episodes == 0:
            self.metrics.make_plots()

        if self.completed_episodes >= self.total_episodes:
            self.finished = True
            self.agent.save(self.latest_model_path, metadata={**metadata, "final": True})
            self.metrics.make_plots()

    def save_now(self) -> Path:
        return self.agent.save(
            self.latest_model_path,
            metadata={
                "track": self.env.track.name,
                "episode": self.episode_number,
                "episode_reward": self.env.episode_reward,
                "run_dir": str(self.run_dir),
                "manual_save": True,
            },
        )

    def status(self) -> LiveTrainingStatus:
        return LiveTrainingStatus(
            episode=self.episode_number,
            episode_reward=self.env.episode_reward,
            episode_steps=self.env.steps,
            epsilon=self.agent.epsilon,
            loss=self.agent.last_loss,
            completed_episodes=self.completed_episodes,
            last_episode=self.last_episode,
            paused=self.paused,
            finished=self.finished,
        )
