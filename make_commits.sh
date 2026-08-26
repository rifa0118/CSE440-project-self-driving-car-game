#!/bin/bash
set -e

# Reset to the initial commit, keeping all files in working directory untracked
git reset 5a2cbfe

# 1. Base Game setup
git add requirements.txt main.py support/config.py support/setup_windows.bat support/run_game.bat support/utils/
git commit -m "add basic game config and setup scripts"

# 2. Game Core (Car, Environment, Physics)
git add support/game/
git commit -m "build game physics and rendering engine"

# 3. AI Agent (DQN)
git add support/ai/ support/train_easy.bat support/evaluate_easy.bat
git commit -m "implement deep q-learning agent and training loops"

# 4. Pretrained Models and Results
git add data/
git commit -m "add pre-trained models and evaluation metrics"

# 5. Tests and Tools
git add support/tests/ support/tools/ support/scripts/ support/verification/ support/requirements-dev.txt support/pyproject.toml support/verify_project.bat support/verify_project.sh support/commit_script.sh
git commit -m "add unit tests and verification tools"

# 6. Documentation and Reports
git add support/docs/ others/ support/RELEASE_NOTES.md support/SHA256SUMS.txt
git commit -m "write project report, viva qa and presentation slides"

# 7. Final Polish (README and anything else)
git add -A
git commit -m "final polish and directory reorganization for submission"

git push -f origin HEAD:main HEAD:istiaque
