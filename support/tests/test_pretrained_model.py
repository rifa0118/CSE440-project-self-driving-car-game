from __future__ import annotations

import pytest

from ai.agent import DQNAgent
from config import MODELS_DIR
from game.environment import RacingEnv


@pytest.mark.parametrize("track", ["easy", "medium", "hard"])
def test_included_best_model_completes_a_lap_without_collision(track: str) -> None:
    path = MODELS_DIR / f"{track}_best.pth"
    assert path.exists(), f"The release should include the demonstrated {track}-track best model"
    agent, metadata = DQNAgent.from_checkpoint(path, device="cpu")
    assert metadata["track"] == track
    env = RacingEnv(track)
    state = env.reset(seed=1)
    terminated = truncated = False
    info = {}
    while not (terminated or truncated):
        action = agent.select_action(state, evaluate=True)
        state, _, terminated, truncated, info = env.step(action)
    assert info["termination_reason"] == "lap_complete"
    assert env.lap_count == 1
    assert env.collision_count == 0
