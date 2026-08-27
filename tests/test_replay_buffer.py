from __future__ import annotations

import numpy as np

from ai.replay_buffer import ReplayBuffer


def test_replay_buffer_adds_and_samples_transitions() -> None:
    buffer = ReplayBuffer(capacity=20, state_size=6, seed=1)
    for index in range(10):
        state = np.full(6, index, dtype=np.float32)
        buffer.add(state, index % 4, float(index), state + 1.0, index % 3 == 0)

    batch = buffer.sample(4, "cpu")
    assert len(buffer) == 10
    assert batch.states.shape == (4, 6)
    assert batch.actions.shape == (4, 1)
    assert batch.rewards.shape == (4, 1)
    assert batch.next_states.shape == (4, 6)
    assert batch.dones.shape == (4, 1)
