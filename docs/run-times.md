# How long runs take

Wall-clock minutes of the long runs on this machine (M4 Max, 64 GB), so a run can
be estimated before it starts. `experiments/timed.sh` appends a row per run; the
label says how warm the caches were, which matters more than the page count. A run
with nothing cached costs about **0.8 min per page** for a trust-data rebuild
(glm-ocr, tesseract and qwen3.8 per line, then clef and winnow per suspect).

| Date | Run | Pages | Minutes | Exit |
| --- | --- | --- | --- | --- |
| 2026-10-07 | trust data, Goede dochter (Qwen readings cached by the line bench) | 56 | 3 | 0 |
| 2026-10-07 | trust data, Vals alarm, cold | 50 | 39 | 0 |
| 2026-10-07 | trust data, Crime, cold | 94 | 81 | 0 |
| 2026-10-08 | trust data, Goede dochter, short lines only new | 56 | 2 | 0 |
