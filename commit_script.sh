#!/bin/bash
git update-ref -d HEAD
git rm -r --cached .

git add .gitignore config.py setup_windows.bat train_easy.bat run_game.bat verify_project.bat verify_project.sh
git commit -m "Initial project setup and configurations"

git add game/track.py game/car.py game/sensors.py
git commit -m "Add core game models and track layouts"

git add game/renderer.py assets/
git commit -m "Implement rendering engine and sidebar UI"

git add ai/network.py ai/replay_buffer.py ai/agent.py
git commit -m "Add Deep Q-Network agent and replay buffer"

git add game/environment.py ai/trainer.py ai/live_trainer.py
git commit -m "Implement Pygame training loop and RL environment"

git add game/app.py main.py
git commit -m "Add main application controller and menu states"

git add utils/ scripts/ tools/
git commit -m "Add utility scripts and metrics tracking"

git add tests/ submission/ verification/
git commit -m "Include unit tests, documentation, and verification reports"

git add models/ results/
git commit -m "Add pre-trained models and evaluation results"

# Any leftover files
git add .
git commit -m "Final polish and minor tweaks"

git push -u origin HEAD:istiaque --force
