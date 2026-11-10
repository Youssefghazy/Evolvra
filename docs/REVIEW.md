# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-10, after STATUS `7b4813d` (round 15)._

## Verdict
- **QA-REPORT.md works without hand-holding.** The sprint-prioritizer QA wrote it from the 0.3.8 template alone,
  and brute-forced all 512 subsets to prove the plan optimal. Excellent.
- The demo film is in, and I reviewed it frame by frame (see the end).

## Fixed (tests 76, ruff clean; no plugin change)
1. **Report-less QA folders** (your open question 1): for QA agents (evidence-collector, reality-checker) with no
   report file, the **transcript/results lead**, and the QA's own driver scripts get at most 1,500 characters.
   Tested with your frontend layout (15 KB driver, 6 KB transcript): the whole transcript is visible. Builders
   are unchanged.
2. **Film:** moved to `dashboard/public/media/evolvra-demo.mp4` (git keeps one copy) with a poster. The Overview
   page has a "Watch the film" card with a lightbox player, and the README embeds the poster and links to the film.

## Decisions
- **A re-score that lowers a score** (your open question 2): allowed. Re-score only when the judge input changes,
  and always report before/after, as you do. The judges' latest verdict is the record. Never cherry-pick runs.

## Requested now (short round)
1. `git pull`, tests: **expect 76**, ruff clean.
2. Re-score the frontend mission once more (its input changes again; 3 calls):
   `uv run evolvra score --mission 20261110-051125-build-a-single-file --rescore`. Report the QA task per judge.
3. One mission for **content-creator** or **rapid-prototyper** (your open question 3).
4. `.\scripts\cycle.ps1` (no `-Evolve`), outside :15–:50. Short STATUS with `-- docs/STATUS.md`.

## Film review (for Youssef; nothing for the operator)
42.5 s, 1080p60, no audio. The story and every number check out against the records: Evidence Collector arena
0.63 → 0.80, promotions at generations 4 and 12, 13 generations, 11 refused, 2 promoted, $0. One factual error:
**Judge #2 is shown as "Qwen, Alibaba lineage"; since 5 Nov it is Nemotron (NVIDIA lineage, on OpenRouter).**
Mission and task counts (23 / 45) are a little behind (now 25 / 49), which is fine for a dated snapshot.
