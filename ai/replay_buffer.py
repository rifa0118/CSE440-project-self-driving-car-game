"""Fixed-size experience replay memory for stable DQN training."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True, slots=True)
class ReplayBatch:
    states: torch.Tensor
    actions: torch.Tensor
    rewards: torch.Tensor
    next_states: torch.Tensor
    dones: torch.Tensor


class ReplayBuffer:
    def __init__(self, capacity: int, state_size: int, seed: int = 440) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if state_size <= 0:
            raise ValueError("state_size must be positive")
        self.capacity = int(capacity)
        self.state_size = int(state_size)
        self._rng = np.random.default_rng(seed)
        self._states = np.zeros((capacity, state_size), dtype=np.float32)
        self._actions = np.zeros(capacity, dtype=np.int64)
        self._rewards = np.zeros(capacity, dtype=np.float32)
        self._next_states = np.zeros((capacity, state_size), dtype=np.float32)
        self._dones = np.zeros(capacity, dtype=np.float32)
        self._position = 0
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        state_array = np.asarray(state, dtype=np.float32)
        next_state_array = np.asarray(next_state, dtype=np.float32)
        if state_array.shape != (self.state_size,):
            raise ValueError(f"state must have shape {(self.state_size,)}, got {state_array.shape}")
        if next_state_array.shape != (self.state_size,):
            raise ValueError(
                f"next_state must have shape {(self.state_size,)}, got {next_state_array.shape}"
            )

        index = self._position
        self._states[index] = state_array
        self._actions[index] = int(action)
        self._rewards[index] = float(reward)
        self._next_states[index] = next_state_array
        self._dones[index] = float(bool(done))
        self._position = (self._position + 1) % self.capacity
        self._size = min(self._size + 1, self.capacity)

    def sample(self, batch_size: int, device: torch.device | str) -> ReplayBatch:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self._size < batch_size:
            raise ValueError(f"Cannot sample {batch_size} transitions from buffer of size {self._size}")
        indices = self._rng.choice(self._size, size=batch_size, replace=False)
        target_device = torch.device(device)
        return ReplayBatch(
            states=torch.as_tensor(self._states[indices], device=target_device),
            actions=torch.as_tensor(self._actions[indices], device=target_device).unsqueeze(1),
            rewards=torch.as_tensor(self._rewards[indices], device=target_device).unsqueeze(1),
            next_states=torch.as_tensor(self._next_states[indices], device=target_device),
            dones=torch.as_tensor(self._dones[indices], device=target_device).unsqueeze(1),
        )
