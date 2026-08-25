"""Central configuration for the self-driving car project.

The values deliberately keep the simulation lightweight enough for CPU-only
training while preserving the requirements in the project plan: five distance
sensors plus speed, four actions, and a small 6-64-64-4 DQN.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
TRACKS_DIR = ASSETS_DIR / "tracks"
MODELS_DIR = PROJECT_ROOT / "models"
RESULTS_DIR = PROJECT_ROOT / "results"


@dataclass(slots=True)
class SimulationConfig:
    """Physics, sensors, and episode limits."""

    width: int = 1280
    height: int = 800
    fps: int = 60
    max_speed: float = 7.0
    acceleration: float = 0.20
    brake_power: float = 0.34
    friction: float = 0.035
    steering_rate_deg: float = 4.2
    car_length: float = 30.0
    car_width: float = 16.0
    sensor_angles_deg: tuple[float, ...] = (-90.0, -45.0, 0.0, 45.0, 90.0)
    sensor_max_distance: float = 165.0
    sensor_step: float = 2.0
    max_steps: int = 1_800
    target_laps: int = 1
    stuck_speed_threshold: float = 0.18
    stuck_step_limit: int = 180
    checkpoint_count: int = 12
    traffic_count: int = 3
    traffic_speed: float = 2.0

    @property
    def state_size(self) -> int:
        return len(self.sensor_angles_deg) + 1

    @property
    def action_size(self) -> int:
        return 4


@dataclass(slots=True)
class RewardConfig:
    """Reward values taken directly from the supplied project plan."""

    driving_forward: float = 1.0
    checkpoint: float = 20.0
    lap_complete: float = 100.0
    collision: float = -100.0
    driving_backwards: float = -10.0
    standing_still: float = -2.0


@dataclass(slots=True)
class TrainingConfig:
    """DQN training hyperparameters suitable for a normal laptop."""

    episodes: int = 500
    gamma: float = 0.99
    learning_rate: float = 1.0e-3
    batch_size: int = 128
    replay_capacity: int = 50_000
    replay_warmup: int = 750
    train_every_steps: int = 4
    target_update_steps: int = 600
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_steps: int = 45_000
    gradient_clip_norm: float = 10.0
    hidden_size: int = 128
    seed: int = 440
    checkpoint_every_episodes: int = 25
    plot_every_episodes: int = 25
    double_dqn: bool = True
    device: str = "cpu"
    torch_threads: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    """Top-level application configuration."""

    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    default_track: str = "easy"
    default_car_colour: str = "red"


TRACK_CHOICES = ("easy", "medium", "hard")
CAR_COLOURS: dict[str, tuple[int, int, int]] = {
    "red": (224, 67, 54),
    "blue": (54, 120, 224),
    "green": (60, 181, 95),
}
ACTION_NAMES: tuple[str, ...] = ("turn_left", "turn_right", "straight", "brake")
