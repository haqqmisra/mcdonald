# The beat sweep's tools

ROADMAP.md 0.3, objective 9: the scripts the beat sweep of the PURSUE videos was done with, so that the corpus
statement can be run again by anyone with the videos. They arrive here one by one; this is the first.

| file | what it is |
|---|---|
| `videos.tsv` | The sweep's 126 videos: the PURSUE videos with an object to look at, by the release's file name, and whether the whole-video pass followed objects in each. |
| `holdout.py`, `holdout.tsv` | The held-out third (the ideas bank's D5): 42 videos drawn on 2026-10-17, before the gate work, by a hash anyone can repeat. They are not looked at until the gates are frozen on the controls and the rest; then the gates run on them once. `python3 tools/sweep/holdout.py` draws again and checks the table; `--list` prints the ids for a script to skip. |
