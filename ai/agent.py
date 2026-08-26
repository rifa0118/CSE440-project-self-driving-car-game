"""Deep Q-Network agent with replay memory and a target network."""

from __future__ import annotations

import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.optim import Adam

from ai.network import DQN
from ai.replay_buffer import ReplayBuffer
from config import TrainingConfig
from utils.seed import seed_everything


class DQNAgent:
    CHECKPOINT_FORMAT_VERSION = 1

    def __init__(
        self,
        state_size: int,
        action_size: int,
        config: TrainingConfig | None = None,
    ) -> None:
        self.config = config or TrainingConfig()
        self.state_size = int(state_size)
        self.action_size = int(action_size)
        self.device = self._resolve_device(self.config.device)
        if self.device.type == "cpu":
            torch.set_num_threads(max(1, int(self.config.torch_threads)))
        seed_everything(self.config.seed)
        self._rng = np.random.default_rng(self.config.seed)

        self.policy_net = DQN(
            state_size=self.state_size,
            action_size=self.action_size,
            hidden_size=self.config.hidden_size,
        ).to(self.device)
        self.target_net = DQN(
            state_size=self.state_size,
            action_size=self.action_size,
            hidden_size=self.config.hidden_size,
        ).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = Adam(self.policy_net.parameters(), lr=self.config.learning_rate)
        self.loss_function = nn.SmoothL1Loss()
        self.replay_buffer = ReplayBuffer(
            capacity=self.config.replay_capacity,
            state_size=self.state_size,
            seed=self.config.seed,
        )
        self.global_step = 0
        self.optimisation_steps = 0
        self.last_loss: float | None = None

    @staticmethod
    def _resolve_device(requested: str) -> torch.device:
        requested = requested.lower().strip()
        if requested == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if requested.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but no CUDA device is available")
        return torch.device(requested)

    @property
    def epsilon(self) -> float:
        progress = min(1.0, self.global_step / max(1, self.config.epsilon_decay_steps))
        return float(
            self.config.epsilon_start
            + progress * (self.config.epsilon_end - self.config.epsilon_start)
        )

    def select_action(self, state: np.ndarray, *, evaluate: bool = False) -> int:
        state_array = np.asarray(state, dtype=np.float32)
        if state_array.shape != (self.state_size,):
            raise ValueError(f"state must have shape {(self.state_size,)}, got {state_array.shape}")
        if not evaluate and self._rng.random() < self.epsilon:
            return int(self._rng.integers(self.action_size))

        with torch.inference_mode():
            state_tensor = torch.as_tensor(state_array, device=self.device).unsqueeze(0)
            q_values = self.policy_net(state_tensor)
            return int(q_values.argmax(dim=1).item())

    def observe(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> float | None:
        self.replay_buffer.add(state, action, reward, next_state, done)
        self.global_step += 1

        if len(self.replay_buffer) < max(self.config.replay_warmup, self.config.batch_size):
            return None
        if self.global_step % self.config.train_every_steps != 0:
            return None

        loss = self._optimise_model()
        if self.global_step % self.config.target_update_steps == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        return loss

    def _optimise_model(self) -> float:
        batch = self.replay_buffer.sample(self.config.batch_size, self.device)
        current_q = self.policy_net(batch.states).gather(1, batch.actions)

        with torch.no_grad():
            if self.config.double_dqn:
                next_actions = self.policy_net(batch.next_states).argmax(dim=1, keepdim=True)
                next_q = self.target_net(batch.next_states).gather(1, next_actions)
            else:
                next_q = self.target_net(batch.next_states).max(dim=1, keepdim=True).values
            target_q = batch.rewards + self.config.gamma * (1.0 - batch.dones) * next_q

        loss = self.loss_function(current_q, target_q)
        self.optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.config.gradient_clip_norm)
        self.optimizer.step()

        self.optimisation_steps += 1
        self.last_loss = float(loss.detach().cpu().item())
        if not math.isfinite(self.last_loss):
            raise FloatingPointError("DQN loss became non-finite")
        return self.last_loss

    def save(
        self,
        path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "format_version": self.CHECKPOINT_FORMAT_VERSION,
            "state_size": self.state_size,
            "action_size": self.action_size,
            "training_config": asdict(self.config),
            "policy_state_dict": self.policy_net.state_dict(),
            "target_state_dict": self.target_net.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "global_step": self.global_step,
            "optimisation_steps": self.optimisation_steps,
            "last_loss": self.last_loss,
            "metadata": metadata or {},
        }
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        torch.save(checkpoint, temporary)
        temporary.replace(destination)
        return destination

    def load(self, path: str | Path, *, load_optimizer: bool = True) -> dict[str, Any]:
        source = Path(path)
        if not source.exists():
            raise FileNotFoundError(source)
        try:
            checkpoint = torch.load(source, map_location=self.device, weights_only=True)
        except TypeError:  # PyTorch before the weights_only argument
            checkpoint = torch.load(source, map_location=self.device)

        if int(checkpoint.get("format_version", 0)) != self.CHECKPOINT_FORMAT_VERSION:
            raise ValueError("Unsupported checkpoint format")
        if int(checkpoint["state_size"]) != self.state_size:
            raise ValueError("Checkpoint state size does not match this environment")
        if int(checkpoint["action_size"]) != self.action_size:
            raise ValueError("Checkpoint action size does not match this environment")

        self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        self.target_net.load_state_dict(checkpoint.get("target_state_dict", checkpoint["policy_state_dict"]))
        if load_optimizer and "optimizer_state_dict" in checkpoint:
            self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.global_step = int(checkpoint.get("global_step", 0))
        self.optimisation_steps = int(checkpoint.get("optimisation_steps", 0))
        last_loss = checkpoint.get("last_loss")
        self.last_loss = None if last_loss is None else float(last_loss)
        return dict(checkpoint.get("metadata", {}))

    @classmethod
    def from_checkpoint(
        cls,
        path: str | Path,
        *,
        device: str = "cpu",
        load_optimizer: bool = False,
    ) -> tuple["DQNAgent", dict[str, Any]]:
        source = Path(path)
        try:
            checkpoint = torch.load(source, map_location=device, weights_only=True)
        except TypeError:
            checkpoint = torch.load(source, map_location=device)
        config_values = dict(checkpoint.get("training_config", {}))
        config_values["device"] = device
        config = TrainingConfig(**config_values)
        agent = cls(
            state_size=int(checkpoint["state_size"]),
            action_size=int(checkpoint["action_size"]),
            config=config,
        )
        metadata = agent.load(source, load_optimizer=load_optimizer)
        return agent, metadata
