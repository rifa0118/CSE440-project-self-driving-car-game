# Results

Training evidence:

- `pretrained_easy_300_episodes/` — original 300-episode Easy run and the three required graphs.
- `pretrained_medium_curriculum/` — Medium curriculum-continuation metrics and graphs.
- `pretrained_hard_curriculum/` — Hard curriculum-continuation metrics and graphs.

Greedy evaluation evidence:

- `easy_pretrained_evaluation_20.json`
- `medium_pretrained_evaluation_20.json`
- `hard_pretrained_evaluation_20.json`

Each packaged best checkpoint completed 20/20 deterministic greedy episodes from its track's standard start position with zero collisions. These results do not establish random-start generalization.
