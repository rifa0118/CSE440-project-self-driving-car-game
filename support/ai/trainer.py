"""Headless DQN training and evaluation loops."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from ai.agent import DQNAgent
from config import MODELS_DIR, RESULTS_DIR, TrainingConfig
from game.environment import RacingEnv
from utils.metrics import EpisodeMetrics, MetricsStore

ProgressCallback = Callable[[EpisodeMetrics, RacingEnv, DQNAgent], None]


def create_run_directory(track_name: str, base_dir: Path = RESULTS_DIR) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base_dir / f"{track_name}_{timestamp}"
    suffix = 1
    while run_dir.exists():
        run_dir = base_dir / f"{track_name}_{timestamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


class Trainer:
    def __init__(
        self,
        env: RacingEnv,
        agent: DQNAgent,
        *,
        training_config: TrainingConfig | None = None,
        run_dir: str | Path | None = None,
        model_dir: str | Path = MODELS_DIR,
    ) -> None:
        self.env = env
        self.agent = agent
        self.config = training_config or agent.config
        self.run_dir = Path(run_dir) if run_dir is not None else create_run_directory(env.track.name)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = MetricsStore(self.run_dir)
        self.best_score: tuple[int, float] = (-1, float("-inf"))
        self.best_model_path = self.model_dir / f"{env.track.name}_best.pth"
        self.latest_model_path = self.model_dir / f"{env.track.name}_latest.pth"
        self._write_run_config()

    def _write_run_config(self) -> None:
        payload = {
            "track": self.env.track.name,
            "environment": self.env.describe(),
            "training": asdict(self.config),
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
        with (self.run_dir / "run_config.json").open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def train(
        self,
        episodes: int | None = None,
        *,
        start_episode: int = 1,
        progress_callback: ProgressCallback | None = None,
        verbose: bool = True,
        generate_plots: bool = True,
    ) -> MetricsStore:
        total_episodes = int(episodes if episodes is not None else self.config.episodes)
        if total_episodes <= 0:
            raise ValueError("episodes must be positive")

        started = time.perf_counter()
        for episode in range(start_episode, start_episode + total_episodes):
            state = self.env.reset(seed=self.config.seed + episode)
            losses: list[float] = []
            terminated = False
            truncated = False
            info: dict[str, Any] = {"termination_reason": None}

            while not (terminated or truncated):
                action = self.agent.select_action(state)
                next_state, reward, terminated, truncated, info = self.env.step(action)
                loss = self.agent.observe(
                    state,
                    action,
                    reward,
                    next_state,
                    terminated or truncated,
                )
                if loss is not None:
                    losses.append(loss)
                state = next_state

            episode_metrics = EpisodeMetrics(
                episode=episode,
                reward=self.env.episode_reward,
                steps=self.env.steps,
                laps=self.env.lap_count,
                lap_time_steps=self.env.steps if self.env.lap_count > 0 else None,
                collisions=self.env.collision_count,
                completed=self.env.lap_count > 0,
                epsilon=self.agent.epsilon,
                mean_loss=mean(losses) if losses else None,
                termination_reason=info.get("termination_reason"),
            )
            self.metrics.append(episode_metrics)
            self.metrics.save()
            self._save_checkpoints(episode_metrics)

            if generate_plots and (
                episode % self.config.plot_every_episodes == 0
                or episode == start_episode + total_episodes - 1
            ):
                self.metrics.make_plots()

            if verbose:
                elapsed = time.perf_counter() - started
                loss_text = "n/a" if episode_metrics.mean_loss is None else f"{episode_metrics.mean_loss:.4f}"
                print(
                    f"Episode {episode:4d} | reward {episode_metrics.reward:8.1f} | "
                    f"steps {episode_metrics.steps:4d} | lap {int(episode_metrics.completed)} | "
                    f"epsilon {episode_metrics.epsilon:.3f} | loss {loss_text} | "
                    f"{episode_metrics.termination_reason or '-'} | elapsed {elapsed:6.1f}s",
                    flush=True,
                )

            if progress_callback is not None:
                progress_callback(episode_metrics, self.env, self.agent)

        self.metrics.save()
        if generate_plots:
            self.metrics.make_plots()
        return self.metrics

    def _save_checkpoints(self, episode: EpisodeMetrics) -> None:
        metadata = {
            "track": self.env.track.name,
            "episode": episode.episode,
            "episode_reward": episode.reward,
            "completed": episode.completed,
            "run_dir": str(self.run_dir),
        }
        score = (int(episode.completed), episode.reward)
        if score > self.best_score:
            self.best_score = score
            self.agent.save(self.best_model_path, metadata=metadata)

        if (
            episode.episode % self.config.checkpoint_every_episodes == 0
            or episode.episode == 1
        ):
            self.agent.save(self.latest_model_path, metadata=metadata)

    def save_final(self, episode_number: int) -> Path:
        return self.agent.save(
            self.latest_model_path,
            metadata={
                "track": self.env.track.name,
                "episode": episode_number,
                "run_dir": str(self.run_dir),
                "final": True,
            },
        )


def evaluate_agent(
    env: RacingEnv,
    agent: DQNAgent,
    *,
    episodes: int = 20,
    seed: int = 10_000,
    verbose: bool = True,
) -> dict[str, Any]:
    if episodes <= 0:
        raise ValueError("episodes must be positive")
    episode_results: list[dict[str, Any]] = []

    for episode in range(1, episodes + 1):
        state = env.reset(seed=seed + episode)
        terminated = False
        truncated = False
        info: dict[str, Any] = {"termination_reason": None}
        while not (terminated or truncated):
            action = agent.select_action(state, evaluate=True)
            state, _, terminated, truncated, info = env.step(action)

        result = {
            "episode": episode,
            "reward": env.episode_reward,
            "steps": env.steps,
            "completed": env.lap_count > 0,
            "laps": env.lap_count,
            "collisions": env.collision_count,
            "termination_reason": info.get("termination_reason"),
        }
        episode_results.append(result)
        if verbose:
            print(
                f"Evaluation {episode:3d} | reward {result['reward']:8.1f} | "
                f"steps {result['steps']:4d} | completed {int(result['completed'])} | "
                f"{result['termination_reason']}",
                flush=True,
            )

    completed = [result for result in episode_results if result["completed"]]
    summary = {
        "episodes": episodes,
        "success_rate": len(completed) / episodes,
        "mean_reward": mean(result["reward"] for result in episode_results),
        "best_reward": max(result["reward"] for result in episode_results),
        "mean_lap_steps": mean(result["steps"] for result in completed) if completed else None,
        "total_collisions": sum(result["collisions"] for result in episode_results),
        "episode_results": episode_results,
    }
    return summary
