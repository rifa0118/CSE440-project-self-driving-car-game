from __future__ import annotations

import numpy as np
import torch

from ai.agent import DQNAgent
from config import TrainingConfig


def test_agent_optimises_and_round_trips_checkpoint(tmp_path) -> None:
    config = TrainingConfig(
        batch_size=8,
        replay_warmup=8,
        replay_capacity=100,
        train_every_steps=1,
        target_update_steps=5,
        epsilon_decay_steps=100,
        torch_threads=1,
    )
    agent = DQNAgent(6, 4, config)
    state = np.zeros(6, dtype=np.float32)
    for index in range(20):
        next_state = np.full(6, (index + 1) / 20.0, dtype=np.float32)
        agent.observe(state, index % 4, 1.0, next_state, index == 19)
        state = next_state

    assert agent.last_loss is not None
    path = agent.save(tmp_path / "model.pth", metadata={"episode": 7})
    restored = DQNAgent(6, 4, config)
    metadata = restored.load(path)
    assert metadata == {"episode": 7}
    assert restored.global_step == agent.global_step
    for original, loaded in zip(
        agent.policy_net.parameters(),
        restored.policy_net.parameters(),
        strict=True,
    ):
        assert torch.equal(original, loaded)
