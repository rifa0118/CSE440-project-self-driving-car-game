# Models

Packaged best checkpoints:

- `easy_best.pth`: selected during the original 300-episode Easy DQN run.
- `medium_best.pth`: curriculum continuation from `easy_best.pth` on the Medium track.
- `hard_best.pth`: curriculum continuation from `medium_best.pth` on the Hard track.

Each `*_best.pth` checkpoint completed 20/20 deterministic greedy evaluation episodes from that track's standard start position with zero collisions. This is evidence for the packaged start condition, not random-start or real-world generalization.

`*_latest.pth` files are resume checkpoints from the corresponding training process. Watch Trained AI prefers `*_best.pth` when both exist.
