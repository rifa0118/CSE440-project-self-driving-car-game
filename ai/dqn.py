from torch import nn


class DQN(nn.Module):
    """Dueling Deep Q-Network.

    Architecture splits into two streams after shared feature extraction:
      - Value stream V(s):     estimates how good a state is regardless of action
      - Advantage stream A(s,a): estimates the relative benefit of each action

    Combined as: Q(s,a) = V(s) + A(s,a) - mean(A(s,:))

    This decomposition helps the network learn which states are valuable
    independently of actions, dramatically improving learning efficiency
    for states where the action choice doesn't matter much (e.g. straight road).
    """

    def __init__(self, input_dim, output_dim):
        super().__init__()

        # ── Shared feature extraction ─────────────────────────────────────────
        self.feature = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
        )

        # ── Value stream V(s) ─────────────────────────────────────────────────
        self.value_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

        # ── Advantage stream A(s, a) ─────────────────────────────────────────
        self.advantage_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.ReLU(),
            nn.Linear(128, output_dim),
        )

        # ── Weight initialization ─────────────────────────────────────────────
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=1.0)
                nn.init.zeros_(module.bias)
        # Small init for output heads to start near zero
        nn.init.orthogonal_(self.value_stream[-1].weight, gain=0.01)
        nn.init.orthogonal_(self.advantage_stream[-1].weight, gain=0.01)

    def forward(self, x):
        features = self.feature(x)
        value = self.value_stream(features)  # (batch, 1)
        advantage = self.advantage_stream(features)  # (batch, actions)
        # Combine: Q = V + (A - mean(A))
        q = value + advantage - advantage.mean(dim=1, keepdim=True)
        return q
