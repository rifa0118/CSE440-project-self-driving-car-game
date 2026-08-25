"""Training/evaluation metric storage and presentation graphs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


@dataclass(slots=True)
class EpisodeMetrics:
    episode: int
    reward: float
    steps: int
    laps: int
    lap_time_steps: int | None
    collisions: int
    completed: bool
    epsilon: float
    mean_loss: float | None
    termination_reason: str | None

    @property
    def lap_time_seconds(self) -> float | None:
        if self.lap_time_steps is None:
            return None
        return self.lap_time_steps / 60.0

    def to_dict(self) -> dict[str, object]:
        values = asdict(self)
        values["lap_time_seconds"] = self.lap_time_seconds
        return values


class MetricsStore:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.episodes: list[EpisodeMetrics] = []

    def append(self, metrics: EpisodeMetrics) -> None:
        self.episodes.append(metrics)

    def extend(self, metrics: Iterable[EpisodeMetrics]) -> None:
        self.episodes.extend(metrics)

    def save(self) -> None:
        self._save_csv()
        self._save_json()

    def _save_csv(self) -> None:
        path = self.output_dir / "metrics.csv"
        rows = [episode.to_dict() for episode in self.episodes]
        if not rows:
            return
        temporary = path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        temporary.replace(path)

    def _save_json(self) -> None:
        path = self.output_dir / "summary.json"
        payload = {
            "summary": self.summary(),
            "episodes": [episode.to_dict() for episode in self.episodes],
        }
        temporary = path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        temporary.replace(path)

    def summary(self, recent_window: int = 50) -> dict[str, object]:
        if not self.episodes:
            return {
                "episode_count": 0,
                "success_rate": 0.0,
                "best_reward": None,
                "recent_average_reward": None,
                "mean_completed_lap_time_seconds": None,
                "total_collisions": 0,
            }
        recent = self.episodes[-recent_window:]
        completed = [episode for episode in self.episodes if episode.completed]
        lap_times = [
            episode.lap_time_seconds
            for episode in completed
            if episode.lap_time_seconds is not None
        ]
        return {
            "episode_count": len(self.episodes),
            "success_rate": len(completed) / len(self.episodes),
            "best_reward": max(episode.reward for episode in self.episodes),
            "recent_average_reward": mean(episode.reward for episode in recent),
            "mean_completed_lap_time_seconds": mean(lap_times) if lap_times else None,
            "total_collisions": sum(episode.collisions for episode in self.episodes),
        }

    def make_plots(self, rolling_window: int = 20) -> None:
        if not self.episodes:
            return
        episode_numbers = np.asarray([item.episode for item in self.episodes])
        rewards = np.asarray([item.reward for item in self.episodes], dtype=np.float64)
        collisions = np.asarray([item.collisions for item in self.episodes], dtype=np.float64)

        plt.figure(figsize=(10, 5.5))
        plt.plot(episode_numbers, rewards, linewidth=1.0, alpha=0.55, label="Episode reward")
        if len(rewards) >= rolling_window:
            kernel = np.ones(rolling_window) / rolling_window
            rolling = np.convolve(rewards, kernel, mode="valid")
            rolling_episodes = episode_numbers[rolling_window - 1 :]
            plt.plot(rolling_episodes, rolling, linewidth=2.0, label=f"{rolling_window}-episode average")
        plt.xlabel("Episode")
        plt.ylabel("Total reward")
        plt.title("Reward per Episode")
        plt.grid(alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.output_dir / "reward_per_episode.png", dpi=160)
        plt.close()

        completed = [item for item in self.episodes if item.lap_time_seconds is not None]
        plt.figure(figsize=(10, 5.5))
        if completed:
            plt.plot(
                [item.episode for item in completed],
                [item.lap_time_seconds for item in completed],
                marker="o",
                linewidth=1.5,
            )
        else:
            plt.text(0.5, 0.5, "No completed laps yet", ha="center", va="center", transform=plt.gca().transAxes)
        plt.xlabel("Episode")
        plt.ylabel("Lap time (seconds at 60 FPS)")
        plt.title("Lap Time per Completed Episode")
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(self.output_dir / "lap_time_per_episode.png", dpi=160)
        plt.close()

        plt.figure(figsize=(10, 5.5))
        plt.plot(episode_numbers, collisions, linewidth=1.3)
        plt.xlabel("Episode")
        plt.ylabel("Collision count")
        plt.yticks([0, 1])
        plt.title("Collision Count per Episode")
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(self.output_dir / "collision_count_per_episode.png", dpi=160)
        plt.close()
