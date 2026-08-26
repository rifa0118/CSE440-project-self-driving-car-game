from __future__ import annotations

import torch

from ai.network import DQN


def test_dqn_has_required_input_and_output_shape() -> None:
    network = DQN(state_size=6, action_size=4, hidden_size=64)
    output = network(torch.zeros((8, 6), dtype=torch.float32))
    assert output.shape == (8, 4)
    linear_layers = [module for module in network.modules() if isinstance(module, torch.nn.Linear)]
    assert [(layer.in_features, layer.out_features) for layer in linear_layers] == [
        (6, 64),
        (64, 64),
        (64, 4),
    ]
