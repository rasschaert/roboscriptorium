# How long runs take

Wall-clock minutes of the long runs on this machine (M4 Max, 64 GB), so a run can
be estimated before it starts. `experiments/timed.sh` appends a row per run; the
label says how warm the caches were, which matters more than the page count. A run
with nothing cached costs **0.8–1.1 min per page** for a trust-data rebuild
(glm-ocr, tesseract and qwen3.8 per line, then clef and winnow per suspect).

A run made partly or wholly in macOS Low Power Mode (the battery can't keep up with
Ollama even on the charger) says so in its label and doesn't count towards the
estimate. It slows model runs by half or more: Qwen's page reading went from about 200
pages an hour to 113 over a stretch only partly in Low Power Mode (2026-10-14).

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
| 2026-10-09 | bench tuning, scene breaks, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, scene breaks, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, line roles by trees, new lines read locally | 839 | 4 | 0 |
| 2026-10-09 | bench validation, line roles by trees | 250 | 5 | 0 |
| 2026-10-09 | bench tuning, line roles by trees, repeated headings are running heads, warm | 839 | 1 | 0 |
| 2026-10-09 | bench validation, line roles by trees, repeated headings, warm | 250 | 0 | 0 |
| 2026-10-09 | bench tuning, trees keep doubtful lines, edge repeats are furniture | 839 | 3 | 0 |
| 2026-10-09 | bench validation, trees keep doubtful lines, edge repeats are furniture | 250 | 1 | 0 |
| 2026-10-10 | trust data, all books, Qwen read locally where it was hosted (~30.6k lines) | 0 | 542 | 0 |
| 2026-10-10 | arbiter retrained on local Qwen readings | 0 | 1 | 0 |
| 2026-10-10 | bench tuning, Qwen read locally, Thief-Taker read during it | 839 | 45 | 0 |
| 2026-10-10 | bench validation, Qwen read locally | 250 | 0 | 0 |
| 2026-10-10 | bench tuning, slip rate pooled 10 of 100, warm | 839 | 1 | 0 |
| 2026-10-10 | bench validation, slip rate pooled 10 of 100, warm | 250 | 0 | 0 |
| 2026-10-10 | bench tuning, quote questions with three readings | 839 | 1 | 0 |
| 2026-10-10 | bench validation, quote questions with three readings | 250 | 0 | 0 |
| 2026-10-10 | trust data, five books lengthened (~446 new pages), cold, Qwen local | 446 | 447 | 0 |
| 2026-10-10 | arbiter retrained on the longer slices | 0 | 1 | 0 |
| 2026-10-10 | sorter lines rebuilt and scored, longer slices | 0 | 1 | 0 |
| 2026-10-10 | sorter retrained, longer slices | 0 | 0 | 0 |
| 2026-10-10 | bench tuning, longer slices, new baseline | 1285 | 2 | 0 |
| 2026-10-10 | bench validation, longer slices, new baseline | 320 | 1 | 0 |
| 2026-10-10 | bench tuning, longer slices, sorter on | 1285 | 4 | 0 |
| 2026-10-10 | bench validation, longer slices, sorter on | 320 | 1 | 0 |
| 2026-10-11 | trust data, Thief-Taker and five new books (~567 pages), cold, Qwen local | 567 | 525 | 0 |
| 2026-10-11 | arbiter retrained, new sets | 0 | 5 | 0 |
| 2026-10-11 | sorter lines rebuilt and scored, new sets | 0 | 2 | 0 |
| 2026-10-11 | sorter retrained, new sets | 0 | 0 | 0 |
| 2026-10-11 | bench tuning, new sets, new baseline | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, new sets, new baseline | 410 | 1 | 0 |
| 2026-10-11 | bench tuning, new sets, sorter on | 1580 | 5 | 0 |
| 2026-10-11 | bench validation, new sets, sorter on | 410 | 3 | 0 |
| 2026-10-11 | trust data, bughunt fixes, every book, warm | 0 | 5 | 0 |
| 2026-10-11 | arbiter retrained, bughunt fixes | 0 | 6 | 0 |
| 2026-10-11 | bench tuning, bughunt fixes, against the new baseline | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, bughunt fixes, against the new baseline | 410 | 1 | 0 |
| 2026-10-11 | sorter lines rebuilt, validation of 7 books, bughunt merged | 0 | 11 | 0 |
| 2026-10-11 | sorter retrained, without Monterosso | 0 | 0 | 0 |
| 2026-10-11 | bench tuning, sorter on with the running-text guard | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, 7 books, new baseline (Monterosso and De stilte cold) | 590 | 173 | 0 |
| 2026-10-11 | bench validation, 7 books, sorter on with the guard | 590 | 2 | 0 |
| 2026-10-11 | bench tuning, before running-text, small capitals declared | 1580 | 3 | 0 |
| 2026-10-11 | bench tuning, running-text kept and flagged | 1580 | 4 | 0 |
| 2026-10-11 | bench tuning, running-text, sorter on with the guard | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, running-text kept and flagged | 590 | 2 | 0 |
| 2026-10-11 | bench tuning, paragraph breaks in unindented books | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, paragraph breaks in unindented books | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, ask below 0.9 | 1580 | 2 | 0 |
| 2026-10-11 | bench tuning, ask below 0.7 | 1580 | 2 | 0 |
| 2026-10-11 | bench tuning, lost stops before a closing quote asked | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, lost stops before a closing quote asked | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, lost drawn initials flagged | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, lost drawn initials flagged | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, open quotes at a paragraph's end always asked | 1580 | 5 | 0 |
| 2026-10-11 | bench tuning, open quotes at a paragraph's end always asked | 1580 | 5 | 0 |
| 2026-10-11 | bench validation, open quotes at a paragraph's end always asked | 590 | 2 | 0 |
| 2026-10-11 | bench validation, open quotes at a paragraph's end always asked | 590 | 2 | 0 |
| 2026-10-11 | bench tuning, English compounds judged | 1580 | 4 | 0 |
| 2026-10-11 | bench validation, English compounds judged | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, break parts beside the hyphen only | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, break parts beside the hyphen only | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, initial lost before a word in capitals | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, initial lost before a word in capitals | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, open mark after a word asked where it stands | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, open mark after a word asked where it stands | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, no paragraph inside a broken word | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, no paragraph inside a broken word | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, quoted word read without its marks | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, quoted word read without its marks | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, ellipsis after ? or ! spaced as read | 1580 | 2 | 0 |
| 2026-10-11 | bench validation, ellipsis after ? or ! spaced as read | 590 | 1 | 0 |
| 2026-10-11 | probe text reader qwen3.8 + clef crop, Metro 200 paragraphs | 40 | 3 | 0 |
| 2026-10-11 | probe text reader qwen3.8 + clef crop, Goede dochter 200 paragraphs | 40 | 2 | 0 |
| 2026-10-11 | build, Stella, today's build, every stage cached | 67 | 0 | 0 |
| 2026-10-11 | bench tuning, arbiter without its pair prior (ablation) | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, arbiter without its pair prior (ablation) | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, Reis's note marks as printed | 1580 | 3 | 0 |
| 2026-10-11 | bench tuning, scene breaks scored, references rederived | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, scene breaks scored, references rederived | 590 | 2 | 0 |
| 2026-10-11 | bench tuning, scene breaks with opening and closing classes | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, scene breaks with opening and closing classes | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, page-top scene breaks | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, page-top scene breaks | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, page-top scene breaks, flush at the margin | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, page-top scene breaks, flush at the margin | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, page-top scene breaks, flush within 1.5 pt | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, page-top scene breaks, flush within 1.5 pt | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, row slivers don't split runs | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, row slivers don't split runs | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, narrow row slivers don't split runs | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, narrow row slivers don't split runs | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, footnotes out of the text | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, footnotes out of the text | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, footnotes, words checked | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, footnotes, words checked | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, footnotes, light strokes | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, footnotes, light strokes | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, epigraphs | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, epigraphs | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, epigraphs with reading guards | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, epigraphs with reading guards | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, heading labels called page numbers | 1580 | 3 | 0 |
| 2026-10-11 | bench validation, heading labels called page numbers | 590 | 1 | 0 |
| 2026-10-11 | bench tuning, De eerlijke vinder and Monterosso moved to tuning, models retrained | 1772 | 3 | 0 |
| 2026-10-11 | bench validation, after the move, models retrained | 398 | 1 | 0 |
| 2026-10-11 | build, Ex-minnaar, cold | 271 | 306 | 0 |
| 2026-10-11 | build, Ex-minnaar, cached, today's code, from p. 7 | 273 | 1 | 0 |
| 2026-10-11 | bench tuning, lost lines only under a full line | 1772 | 3 | 0 |
| 2026-10-11 | tryout: reader v1, Qwen3.8-Flash-Next UD-IQ1_S via Unsloth Studio (SSD offload) | 550 | 10 | 0 |
| 2026-10-11 | probe: page kinds by clef-flash, labelled set v1, alongside the validation bench | 1034 | 9 | 1 |
| 2026-10-11 | probe: reader readings at 128k vs 8k context, 1 and 4 at a time, alongside the rebuild | 0 | 25 | 0 |
| 2026-10-11 | probe: Qwen throughput at 1-16 requests at a time, and the instructions as system turn, idle machine | 0 | 10 | 0 |
| 2026-10-11 | probe: Qwen throughput at 1-16 requests at a time, OLLAMA_NUM_PARALLEL=4, idle machine | 0 | 8 | 0 |
| 2026-10-11 | probe: glm-ocr throughput at 1, 4, 8 requests at a time, OLLAMA_NUM_PARALLEL=4, idle machine | 0 | 1 | 0 |
| 2026-10-11 | probe: decision models one at a time vs four, OLLAMA_NUM_PARALLEL=4, idle machine | 0 | 2 | 0 |
| 2026-10-11 | tryout: build reader set v2, 17 tuning books, no models | 0 | 8 | 0 |
| 2026-10-12 | tryout: reader v2, qwen3.8:27b-q8_0 on llama.cpp, incumbents read again (work/tryout lost) | 0 | 49 | 0 |
| 2026-10-12 | probe: qwen3.8:27b-q8_0 (llama.cpp, 4 slots) throughput at 1-16 requests at a time, idle machine | 0 | 14 | 0 |
| 2026-10-12 | tryout: reader v2, qwen3.8:27b-mxfp8 | 850 | 0 | 1 |
| 2026-10-12 | trust data, goede-dochter--ia-scan, a shorter slice from its caches | 154 | 136 | 0 |
| 2026-10-12 | trust data, vals-alarm--ia-scan, cold after work/ was lost, Qwen local | 50 | 45 | 0 |
| 2026-10-12 | trust data, the-nature-of-a-crime--doubleday-1924, cold after work/ was lost, Qwen local | 94 | 58 | 0 |
| 2026-10-12 | trust data, the-story-of-doctor-dolittle--stokes-1920, cold after work/ was lost, Qwen local | 180 | 100 | 0 |
| 2026-10-12 | trust data, reis-om-mijn-schedel--ia-scan, a shorter slice from its caches | 245 | 190 | 0 |
| 2026-10-12 | tryout: reader v2, Qwen3.8-27B UD-Q6_K_XL via Unsloth Studio | 850 | 24 | 0 |
| 2026-10-12 | probe: Studio Q6 at 8k, no speculation, 1/2/4 requests at once | 321 | 11 | 0 |
| 2026-10-12 | tryout: reader v2, Qwen3.8-27B UD-Q8_K_XL via Unsloth Studio | 850 | 25 | 0 |
| 2026-10-12 | trust data, afscheid-van-verspilde-tijd--ia-scan, resumed on a stopped run's caches, Qwen local | 62 | 21 | 0 |
| 2026-10-12 | trust data, goede-dochter--ia-scan, a shorter slice from its caches | 91 | 0 | 0 |
| 2026-10-12 | trust data, reis-om-mijn-schedel--ia-scan, a shorter slice from its caches | 89 | 0 | 0 |
| 2026-10-12 | trust data, metro-2033--ia-scan, cold after work/ was lost, Qwen local | 86 | 99 | 0 |
| 2026-10-12 | trust data, de-cipier--ia-scan, cold after work/ was lost, Qwen local | 25 | 23 | 0 |
| 2026-10-12 | trust data, artemis--ia-scan, cold after work/ was lost, Qwen local | 22 | 18 | 0 |
| 2026-10-12 | trust data, 11-22-63--ia-scan, cold after work/ was lost, Qwen local | 18 | 12 | 0 |
| 2026-10-12 | trust data, de-tuin-van-de-avondnevel--ia-scan, cold after work/ was lost, Qwen local | 19 | 21 | 0 |
| 2026-10-12 | trust data, de-eerlijke-vinder--ia-scan, cold after work/ was lost, Qwen local | 84 | 86 | 0 |
| 2026-10-12 | trust data, youre-never-weird-on-the-internet--ia-scan, cold after work/ was lost, Qwen local | 14 | 13 | 0 |
| 2026-10-12 | trust data, the-thief-takers-apprentice--ia-scan, cold after work/ was lost, Qwen local | 16 | 13 | 0 |
| 2026-10-12 | trust data, het-heft-in-eigen-hand--ia-scan, cold after work/ was lost, Qwen local | 25 | 23 | 0 |
| 2026-10-12 | trust data, doodskleed--ia-scan, cold after work/ was lost, Qwen local | 10 | 7 | 0 |
| 2026-10-12 | trust data, het-ijzige-land--ia-scan, cold after work/ was lost, Qwen local | 11 | 12 | 0 |
| 2026-10-12 | trust data, de-kerk-van-de-dode-meisjes--ia-scan, cold after work/ was lost, Qwen local | 17 | 17 | 0 |
| 2026-10-12 | trust data, vuurspel--ia-scan, cold after work/ was lost, Qwen local | 21 | 26 | 0 |
| 2026-10-12 | trust data, monterosso-mon-amour--ia-scan, cold after work/ was lost, Qwen local | 9 | 8 | 0 |
| 2026-10-12 | train arbiter after the rebuild (refused: no Stella data, needed --partial) | 0 | 0 | 1 |
| 2026-10-12 | bench tuning, new baseline after the rebuild (no arbiter saved: failed at once) | 789 | 0 | 1 |
| 2026-10-12 | train arbiter after the rebuild (--partial: no Stella answers since the loss) | 0 | 4 | 0 |
| 2026-10-12 | bench tuning, new baseline after the rebuild (warm but FKA cold) | 789 | 8 | 0 |
| 2026-10-12 | trust data, monterosso-mon-amour--ia-scan, whole book, first 9 pages warm | 88 | 69 | 0 |
| 2026-10-12 | train arbiter (--partial: no Stella answers since the loss) | 0 | 5 | 0 |
| 2026-10-12 | bench tuning, Monterosso whole, warm | 868 | 3 | 0 |
| 2026-10-13 | bench validation, finishing after a halt (8 of 9 books warm) | 916 | 35 | 0 |
| 2026-10-13 | bench tuning, warm, after verdicts and minus-dash fix | 868 | 3 | 0 |
| 2026-10-13 | bench tuning, warm, review fixes, question price and typography | 868 | 3 | 0 |
| 2026-10-13 | bench tuning, warm, straight quotes curled | 868 | 2 | 0 |
| 2026-10-13 | bench tuning, warm, quote after a dash closes | 868 | 2 | 0 |
| 2026-10-13 | bench tuning, warm, measurement out of the CLI (should be identical) | 868 | 2 | 0 |
| 2026-10-13 | bench tuning, warm, three pairs retired, arbiter retrained | 790 | 2 | 0 |
| 2026-10-13 | bench validation, after retiring three pairs (Stranger's Child re-read finishing) | 790 | 34 | 0 |
| 2026-10-13 | line-role trees against the rules, leave one book out (De aanslag cold, the rest warm) | 1000 | 10 | 0 |
| 2026-10-13 | bench tuning, line-role trees on (retrained 2026-10-13), warm | 790 | 5 | 0 |
| 2026-10-13 | line-role trees against the rules, labels without bare-mark lines as body, warm | 1000 | 1 | 0 |
| 2026-10-13 | bench tuning, warm, a fix's leading dash widens the line's box | 790 | 1 | 0 |
| 2026-10-13 | bench validation, warm, a fix's leading dash widens the line's box | 790 | 1 | 0 |
| 2026-10-13 | bench tuning, warm, line-role trees on, labels fixed | 790 | 2 | 0 |
| 2026-10-13 | bench validation, warm, line-role trees on, labels fixed | 790 | 3 | 0 |
| 2026-10-13 | probe: whole-page reading, Qwen and glm-ocr, 19 tuning pages | 19 | 1 | 1 |
| 2026-10-13 | probe: whole-page reading, Qwen and glm-ocr, 19 tuning pages (glm-ocr's image smaller) | 19 | 6 | 0 |
| 2026-10-13 | line-role trees against the rules, with De tunnels' and Steve Jobs' photo slices (those cold) | 1050 | 8 | 0 |
| 2026-10-13 | bench tuning, warm, line-role trees with the photo slices | 790 | 2 | 0 |
| 2026-10-13 | bench validation, warm, line-role trees with the photo slices | 790 | 2 | 0 |
| 2026-10-13 | bench tuning, warm, line-role trees with photo slices, body weight 10 | 790 | 3 | 0 |
| 2026-10-13 | bench validation, warm, line-role trees with photo slices, body weight 10 | 790 | 2 | 0 |
| 2026-10-13 | probe: glm-ocr whole pages as a reader, tuning pages with a pipeline error plus 40 clean | 306 | 28 | 0 |
| 2026-10-14 | probe: glm-ocr and Qwen whole pages, two readers against the pipeline, 306 tuning pages | 306 | 82 | 0 |
| 2026-10-14 | trust data, het-ijzige-land, page readers (trial of tonight's chain) | 11 | 3 | 0 |
| 2026-10-14 | probe: whole-page reading by qwen3.8:27b-mxfp8 against nvfp4, 19 pages | 19 | 7 | 0 |
| 2026-10-14 | trust data, doodskleed, page readers (trial of tonight's chain) | 10 | 3 | 0 |
| 2026-10-15 | page readers read ahead, tuning and validation books | 1000 | 404 | 0 |
| 2026-10-15 | trust data, goede-dochter--ia-scan, page readers | 91 | 12 | 0 |
| 2026-10-15 | trust data, vals-alarm--ia-scan, page readers | 50 | 3 | 0 |
| 2026-10-15 | trust data, the-nature-of-a-crime--doubleday-1924, page readers | 94 | 2 | 0 |
| 2026-10-15 | trust data, the-story-of-doctor-dolittle--stokes-1920, page readers | 180 | 4 | 0 |
| 2026-10-15 | trust data, reis-om-mijn-schedel--ia-scan, page readers | 89 | 6 | 0 |
| 2026-10-15 | trust data, afscheid-van-verspilde-tijd--ia-scan, page readers | 62 | 5 | 0 |
| 2026-10-15 | trust data, metro-2033--ia-scan, page readers | 86 | 4 | 0 |
| 2026-10-15 | trust data, de-cipier--ia-scan, page readers | 25 | 2 | 0 |
| 2026-10-15 | trust data, artemis--ia-scan, page readers | 22 | 0 | 0 |
| 2026-10-15 | trust data, de-tuin-van-de-avondnevel--ia-scan, page readers | 19 | 3 | 0 |
| 2026-10-15 | trust data, de-eerlijke-vinder--ia-scan, page readers | 84 | 7 | 0 |
| 2026-10-15 | trust data, youre-never-weird-on-the-internet--ia-scan, page readers | 14 | 2 | 0 |
| 2026-10-15 | trust data, the-thief-takers-apprentice--ia-scan, page readers | 16 | 0 | 0 |
| 2026-10-15 | trust data, het-heft-in-eigen-hand--ia-scan, page readers | 25 | 3 | 0 |
| 2026-10-15 | trust data, de-kerk-van-de-dode-meisjes--ia-scan, page readers | 17 | 1 | 0 |
| 2026-10-15 | trust data, vuurspel--ia-scan, page readers | 21 | 3 | 0 |
| 2026-10-15 | trust data, monterosso-mon-amour--ia-scan, page readers | 88 | 11 | 0 |
| 2026-10-15 | train arbiter after the rebuild | 0 | 4 | 0 |
| 2026-10-15 | bench tuning after the rebuild, page readers | 838 | 2 | 0 |
| 2026-10-15 | bench validation, page readers | 790 | 48 | 0 |
| 2026-10-15 | probe: reader ablation with the page readers | 0 | 7 | 0 |
| 2026-10-15 | probe: page kinds by clef-flash, the hand-labelled set | 1034 | 0 | 1 |
| 2026-10-15 | tryout reader ornith-1.5:9b, reader set v2 | 850 | 6 | 1 |
| 2026-10-15 | tryout reader ornith-1.5:35b, reader set v2 | 850 | 7 | 0 |
| 2026-10-15 | bench tuning, cold A/A rerun, resumed (32k context) | 790 | 201 | 0 |
| 2026-10-15 | bench tuning, page numbers apart from their line (text layer v7) | 790 | 1 | 1 |
| 2026-10-15 | bench tuning, page numbers apart from their line (text layer v7) | 790 | 64 | 0 |
| 2026-10-15 | bench validation, page numbers split beside full lines (text layer v8) | 790 | 4 | 0 |
| 2026-10-15 | bench tuning, page numbers split beside full lines (text layer v8) | 790 | 5 | 0 |
| 2026-10-16 | build stella, cold (text layer v8) | 67 | 50 | 0 |
| 2026-10-16 | bench tuning, readings keyed without line positions (reading cache v3) | 790 | 2 | 0 |
| 2026-10-16 | probe: retire line-role rules one at a time (warm builds, no OCR check) | 0 | 12 | 1 |
| 2026-10-16 | probe: retire line-role rules one at a time (warm builds, no OCR check, live) | 0 | 7 | 0 |
| 2026-10-16 | train line-role trees, running-text and numeral-slot retired | 0 | 1 | 0 |
| 2026-10-16 | bench tuning, running-text and numeral-slot retired, trees retrained | 790 | 2 | 0 |
| 2026-10-16 | bench validation, running-text and numeral-slot retired, trees retrained | 790 | 2 | 0 |
