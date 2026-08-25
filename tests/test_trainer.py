from __future__ import annotations

from ai.agent import DQNAgent
from ai.trainer import Trainer
from config import SimulationConfig, TrainingConfig
from game.environment import RacingEnv


def test_headless_training_smoke_run_writes_outputs(tmp_path) -> None:
    simulation = SimulationConfig(max_steps=80, stuck_step_limit=40)
    env = RacingEnv("easy", simulation_config=simulation)
    training = TrainingConfig(
        episodes=3,
        batch_size=8,
        replay_warmup=8,
        replay_capacity=200,
        checkpoint_every_episodes=1,
        plot_every_episodes=10,
        train_every_steps=2,
        torch_threads=1,
    )
    agent = DQNAgent(env.state_size, env.action_size, training)
    trainer = Trainer(
        env,
        agent,
        training_config=training,
        run_dir=tmp_path / "run",
        model_dir=tmp_path / "models",
    )
    store = trainer.train(episodes=3, verbose=False, generate_plots=False)
    assert len(store.episodes) == 3
    assert (tmp_path / "run" / "metrics.csv").exists()
    assert (tmp_path / "run" / "summary.json").exists()
    assert trainer.best_model_path.exists()
    assert trainer.latest_model_path.exists()
