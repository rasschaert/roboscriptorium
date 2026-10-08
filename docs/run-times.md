# How long runs take

Wall-clock minutes of the long runs on this machine (M4 Max, 64 GB), so a run can
be estimated before it starts. `experiments/timed.sh` appends a row per run; the
label says how warm the caches were, which matters more than the page count. A run
with nothing cached costs **0.8–1.1 min per page** for a trust-data rebuild
(glm-ocr, tesseract and qwen3.8 per line, then clef and winnow per suspect).

A run made partly or wholly in macOS Low Power Mode (the battery can't keep up with
Ollama even on the charger) says so in its label and doesn't count towards the
estimate: it runs slower by an unmeasured amount.

| Date | Run | Pages | Minutes | Exit |
| --- | --- | --- | --- | --- |
| 2026-10-07 | trust data, Goede dochter (Qwen readings cached by the line bench) | 56 | 3 | 0 |
| 2026-10-07 | trust data, Vals alarm, cold | 50 | 39 | 0 |
| 2026-10-07 | trust data, Crime, cold | 94 | 81 | 0 |
| 2026-10-08 | trust data, Goede dochter, short lines only new | 56 | 2 | 0 |
| 2026-10-08 | trust data, Vals alarm, short lines only new | 50 | 2 | 0 |
| 2026-10-08 | trust data, Crime, short lines only new | 94 | 1 | 0 |
| 2026-10-08 | trust data, Dolittle, cold | 91 | 98 | 0 |
| 2026-10-08 | trust data, De tuin, cold | 42 | 51 | 0 |
| 2026-10-08 | trust data, Grand Hotel Europa, cold | 30 | 32 | 0 |
| 2026-10-08 | trust data, Stella, cold | 67 | 53 | 0 |
| 2026-10-08 | trust data relabel, Crime, warm | 94 | 0 | 0 |
| 2026-10-08 | trust data relabel, Dolittle, warm | 180 | 0 | 0 |
| 2026-10-08 | trust data, Metro 2033 pp. 7-111, cold, partly in Low Power Mode | 105 | 156 | 0 |
| 2026-10-08 | trust data relabel, Metro, warm | 105 | 0 | 0 |
| 2026-10-08 | trust data, Goede dochter, re-read of new crops (Qwen via hosted), alongside Artemis and De cipier | 56 | 2 | 0 |
| 2026-10-08 | trust data, de-tuin-van-de-avondnevel--ia-scan, re-read of new crops (Qwen via hosted), alongside other runs | 42 | 4 | 0 |
| 2026-10-08 | trust data, 11/22/63 pp. 15-94, cold, Qwen via hosted, alongside 2 books and a re-read: stopped by a local model call timing out (Ollama overloaded) | 80 | 14 | 1 |
| 2026-10-08 | trust data, Artemis pp. 13-80, cold, Qwen read via hosted bf16 | 68 | 63 | 0 |
| 2026-10-08 | trust data, the-nature-of-a-crime--doubleday-1924, re-read of new crops (Qwen via hosted), alongside other runs | 94 | 9 | 1 |
| 2026-10-08 | trust data, De cipier pp. 9-92, glm-ocr partly cached, Qwen read via hosted bf16, alongside Artemis | 84 | 47 | 0 |
| 2026-10-08 | trust data, 11/22/63 pp. 15-94, resumed (line roles partly cached), Qwen via hosted, alongside 2 runs | 80 | 35 | 1 |
| 2026-10-08 | trust data, the-nature-of-a-crime--doubleday-1924, re-read of new crops (Qwen via hosted), alongside other runs | 94 | 35 | 1 |
