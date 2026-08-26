"""The small 6-64-64-4 Deep Q-Network from the project plan."""

from __future__ import annotations

import torch
from torch import nn


class DQN(nn.Module):
    """Fully connected Q-network for the six-value sensor state."""

    def __init__(self, state_size: int = 6, action_size: int = 4, hidden_size: int = 64) -> None:
        super().__init__()
        if state_size <= 0 or action_size <= 0 or hidden_size <= 0:
            raise ValueError("network dimensions must be positive")
        self.state_size = int(state_size)
        self.action_size = int(action_size)
        self.hidden_size = int(hidden_size)
        self.layers = nn.Sequential(
            nn.Linear(self.state_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, self.hidden_size),
            nn.ReLU(),
            nn.Linear(self.hidden_size, self.action_size),
        )
        self._initialise_weights()

    def _initialise_weights(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, nonlinearity="relu")
                nn.init.zeros_(module.bias)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.layers(state)
