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
| 2026-10-08 | trust data, the-nature-of-a-crime--doubleday-1924, re-read of new crops (Qwen via hosted), alongside other runs | 94 | 6 | 0 |
| 2026-10-08 | trust data, 11/22/63 pp. 15-94, resumed after an Ollama stall, Qwen via hosted, alongside 1 run | 80 | 46 | 0 |
| 2026-10-08 | trust data, Afscheid pp. 9-70, cold, Qwen via hosted, alongside 2 runs | 62 | 40 | 1 |
| 2026-10-08 | trust data, the-story-of-doctor-dolittle--stokes-1920, re-read of new crops (Qwen via hosted), alongside other runs | 180 | 40 | 1 |
| 2026-10-08 | trust data, the-story-of-doctor-dolittle--stokes-1920, re-read of new crops (Qwen via hosted), alongside other runs | 180 | 3 | 0 |
| 2026-10-08 | trust data, Afscheid pp. 9-70, resumed after a GPU out-of-memory, Qwen via hosted, alongside 2 runs | 62 | 18 | 0 |
| 2026-10-08 | trust data, metro-2033--ia-scan, re-read of new crops (Qwen via hosted), alongside other runs | 105 | 34 | 0 |
| 2026-10-08 | trust data, Reis pp. 11-110, Qwen via hosted, alongside 2 runs | 100 | 46 | 0 |
| 2026-10-08 | trust data, You're Never Weird pp. 13-94, cold, Qwen via hosted, alongside 2 runs | 82 | 66 | 0 |
| 2026-10-08 | trust data, De eerlijke vinder pp. 12-95, cold, Qwen via hosted, alongside 2 runs | 84 | 86 | 0 |
| 2026-10-08 | eval Thief-Taker pp. 11-84, Qwen readings via hosted, warm otherwise | 74 | 14 | 0 |
| 2026-10-08 | bench tuning, fixed rule (baseline), warm (Dolittle re-read by local Qwen) | 839 | 32 | 0 |
| 2026-10-08 | bench tuning, retrained trust, warm | 839 | 1 | 0 |
| 2026-10-08 | bench tuning, ellipsis style, retrained trust, warm | 839 | 1 | 0 |
| 2026-10-08 | bench tuning, ellipsis style, fixed rule, warm | 839 | 1 | 0 |
| 2026-10-08 | bench tuning, ellipsis style, retrained trust against fixed rule, warm | 839 | 1 | 0 |
| 2026-10-08 | trust data, Vals alarm pp. 11-60, whole-body style prompt, Qwen via hosted, alongside 1 run | 50 | 3 | 1 |
| 2026-10-08 | trust data, Dolittle, whole-body style prompt, Qwen via hosted, alongside 1 run | 180 | 5 | 1 |
| 2026-10-08 | trust data, the-story-of-doctor-dolittle--stokes-1920, whole-body style, winnow-ollama:e4b, Qwen cached (hosted for misses), alongside 2 runs | 180 | 14 | 0 |
| 2026-10-08 | trust data, vals-alarm--ia-scan, whole-body style, winnow-ollama:e4b, Qwen cached (hosted for misses), alongside 2 runs | 50 | 14 | 0 |
| 2026-10-08 | tryout: build judge set v1 (11 tuning slices, cached), alongside 1 run | 839 | 5 | 0 |
| 2026-10-08 | tryout: judge v1, imajev:2b, alongside 1 run | 518 | 0 | 1 |
| 2026-10-08 | tryout: judge v1, imajev:4b, alongside 1 run | 518 | 0 | 1 |
| 2026-10-09 | tryout: judge v1, imajev 2B via llama.cpp + readout, alongside 1 run | 518 | 1 | 0 |
| 2026-10-09 | tryout: judge v1, imajev 4B via llama.cpp + readout, alongside 1 run | 518 | 2 | 0 |
| 2026-10-09 | tryout: judge v1, imajev 9B via llama.cpp + readout, alongside 1 run | 518 | 4 | 0 |
| 2026-10-09 | trust data, 12 books, winnow-ollama:e4b as check_model, readings cached, alongside 1 run (11 books; stopped on Stella, DeepInfra down) | 1200 | 61 | 143 |
| 2026-10-09 | trust data, Stella, winnow-ollama:e4b as check_model, local Qwen for the uncached lines | 67 | 4 | 0 |
| 2026-10-09 | bench tuning, winnow-ollama + book-wide style, retrained trust, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, first run (baseline), winnow-ollama, retrained trust | 250 | 0 | 0 |
| 2026-10-09 | trust data, 14 books, imajev-4b as third judge (llama.cpp), readings and other judges cached | 1270 | 31 | 0 |
| 2026-10-09 | bench tuning, imajev-4b third judge, retrained trust, warm | 839 | 3 | 0 |
| 2026-10-09 | bench validation, imajev-4b third judge, retrained trust, warm | 250 | 0 | 0 |
| 2026-10-09 | probe: body range, imajev-4b, alongside 1 run | 250 | 13 | 0 |
| 2026-10-09 | probe: body range, clef-flash:9b, alongside 1 run | 250 | 15 | 0 |
| 2026-10-09 | bench tuning, washed-out pages flagged, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, washed-out pages flagged, warm | 250 | 0 | 0 |
| 2026-10-09 | trust data, 14 books, without Qwen (ablation), other readings cached | 1270 | 19 | 0 |
| 2026-10-09 | bench tuning, without Qwen (ablation) | 839 | 2 | 0 |
| 2026-10-09 | bench validation, without Qwen (ablation) | 250 | 0 | 0 |
| 2026-10-09 | tryout: judge v1, clef:27b re-asked (answer variance) | 518 | 12 | 0 |
| 2026-10-09 | bench tuning, baseline: 9f304c2 + measuring fixes (09fbefe), warm | 839 | 2 | 0 |
| 2026-10-09 | bench validation, baseline: 9f304c2 + measuring fixes, warm | 250 | 1 | 0 |
| 2026-10-09 | trust data, vals-alarm--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, reis-om-mijn-schedel--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 2 | 0 |
| 2026-10-09 | trust data, goede-dochter--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, de-tuin-van-de-avondnevel--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 2 | 0 |
| 2026-10-09 | trust data, de-cipier--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 3 | 0 |
| 2026-10-09 | trust data, stella, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 0 | 0 |
| 2026-10-09 | trust data, metro-2033--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 35 | 0 |
| 2026-10-09 | trust data, the-story-of-doctor-dolittle--stokes-1920, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 4 | 0 |
| 2026-10-09 | trust data, the-nature-of-a-crime--doubleday-1924, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 17 | 0 |
| 2026-10-09 | trust data, afscheid-van-verspilde-tijd--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, 11/22/63 pp. 15-94, fully cold (stages moved aside) after the review's fixes, Qwen via hosted, alongside 2 runs | 80 | 63 | 0 |
| 2026-10-09 | trust data, artemis--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 12 | 0 |
| 2026-10-09 | trust data, de-eerlijke-vinder--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, youre-never-weird-on-the-internet--ia-scan, after the review's fixes (new suspects and changed lines only), Qwen via hosted, alongside 2 runs | 0 | 12 | 0 |
| 2026-10-09 | bench tuning, after the review fixes, retrained trust, warm | 839 | 5 | 0 |
| 2026-10-09 | bench validation, after the review fixes, retrained trust, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, section numbers mid-page, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, section numbers mid-page, warm | 250 | 0 | 0 |
| 2026-10-09 | trust data, stella, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | bench tuning, Qwen second look at 450 dpi as a trust feature (experiment), warm | 839 | 2 | 0 |
| 2026-10-09 | bench validation, Qwen second look (experiment), warm | 250 | 0 | 0 |
| 2026-10-09 | trust data, artemis--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, vals-alarm--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, metro-2033--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 2 | 0 |
| 2026-10-09 | trust data, 11-22-63--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, reis-om-mijn-schedel--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, goede-dochter--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, the-story-of-doctor-dolittle--stokes-1920, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 2 | 0 |
| 2026-10-09 | trust data, de-eerlijke-vinder--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 2 | 0 |
| 2026-10-09 | trust data, de-tuin-van-de-avondnevel--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, the-nature-of-a-crime--doubleday-1924, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 0 | 0 |
| 2026-10-09 | trust data, youre-never-weird-on-the-internet--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, afscheid-van-verspilde-tijd--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | trust data, de-cipier--ia-scan, Qwen second look at 450 dpi (experiment), hosted, alongside 2 runs | 0 | 1 | 0 |
| 2026-10-09 | bench tuning, label numbers kept when the folio is unknown, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, label numbers kept when the folio is unknown, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, a top number is a section where the folio is printed elsewhere, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, top number with the folio elsewhere, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, numeral slots, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, numeral slots, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, faint pages left out of the OCR check, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, faint pages left out of the OCR check, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, faint pages unchecked, ask below 0.9, warm | 839 | 1 | 0 |
| 2026-10-09 | bench tuning, faint pages unchecked, ask below 0.8, warm | 839 | 1 | 0 |
| 2026-10-09 | bench tuning, errors over a page break on the page holding most, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, errors over a page break on the page holding most, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, faint pages out of the OCR check, budget over pages read, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, faint pages out of the OCR check, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, faint out, ask below 0.9, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, faint out, ask below 0.9, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, faint out, ask below 0.8, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, faint out, ask below 0.8, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, ask below 0.8 by default, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, ask below 0.8 by default, warm | 250 | 1 | 0 |
| 2026-10-09 | bench tuning, drawn numbers above sunk openings, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, drawn numbers above sunk openings, warm | 250 | 1 | 0 |
| 2026-10-09 | bench tuning, baseline before the review fixes, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, baseline before the review fixes, warm | 250 | 0 | 0 |
| 2026-10-09 | trust data, all books, ellipsis style folded and spaced quotes labelled, warm readings | 0 | 5 | 0 |
| 2026-10-09 | bench tuning, break errors, per-place catching, washed-out per line, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, break errors, per-place catching, washed-out per line, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, ellipsis style no OCR difference, relabelled and retrained, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, ellipsis style no OCR difference, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, an unseen version never applied, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, an unseen version never applied, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, page margin and gap paragraph starts, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, page margin and gap paragraph starts, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, paragraph starts, gap not after a broken line, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, paragraph starts, gap not after a broken line, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, arbiter calibrated, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, arbiter calibrated, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, hosted share and italics recorded, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, You re Never Weird italics derived, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, each book its own record, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, each book its own record, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, lost lines asked, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, lost lines asked, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, lost lines asked, no specks or notes, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, lost lines asked, no specks or notes, warm | 250 | 0 | 0 |
