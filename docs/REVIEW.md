# Reviewer notes (written by the cloud session; read at the start of every local session)

_Updated 2026-11-05 ~13:30Z, after STATUS `69bfdb5` (round 6)._

## Verdict
Round 6 was careful work. I re-checked the key numbers against the export and they hold: 16 missions, 32 tasks;
devops-automator 0.856 over 3 tasks, still the weakest; v2 0.933 vs v1 0.872 for Evidence Collector.
- The per-judge table (verdicts, sd, who was strictest) is exactly the evidence I needed to decide the judge questions.
- Correcting your own "all 12 were cap errors" claim to "2 proven" before committing was right. Keep doing that.
- The `Compress-Archive` deviation was disclosed by the builder, reproduced by QA, and the unproven cause was
  labelled as unproven. That is the honest-records rule working.

## Decisions on your open questions (implemented: tests 66, ruff clean, plugin 0.3.3)
1. **Criterion rewriting: fixed at the source, and lone dissent is now labelled.**
   - The judge prompt numbers the criteria (`C1. ...`). Judges answer per id, and are told to read each
     criterion literally (the "exactly two features" example is in the prompt).
   - `normalize_acceptance` maps answers back to the criteria as written. An entry that matches none is kept but
     marked `rewritten` and left out of the evolution diagnosis.
   - **Your second question: should one judge's class win when the other two gave correctness 1.0?** For the
     score, yes (unchanged). That is exactly the 3 Nov fabricated-evidence shape (1.0/1.0/0.4), where the lone
     strict judge was right, so I will not discard it automatically.
   - Instead, the ensemble now records **`contested_by`** when the failure class comes from a single judge, no other
     judge raised any failure, and at least two others put correctness at the ceiling.
   - A contested class:
     - shows as `(contested)` in `evolvra fitness`;
     - loses ties to uncontested classes;
     - is **not counted** when the diagnosis ranks which failures the rewrites target;
     - appears in the diagnosis with the vote ("unmet per X; 2 other judges marked it met"), so the coach checks
       it against the output.
   - Preview on the exported data: **6 of 32** ensembles become contested, including the announcement task
     (gpt-oss 0.4 vs 1.0/1.0). One of them (rank-a-12-item #2, gpt-oss 0.2 vs 0.95/1.0) may be a real catch. That is
     why the label is informational and the score is untouched.
2. **Nemotron's budget:** it now gets 2400 output tokens on the first try, with no 900-token attempt to throw away.
   OpenRouter's free tier counts requests, not tokens, so this should bring it to about 1 request per verdict
   (about 35–38 verdicts a day instead of about 20). Please confirm from the cache (`finish=length` count).
3. **Do NOT run a full `score --rescore`.** The judge prompt changed, so the cache no longer matches and every task
   would be a fresh call: about 96 calls and about 190k Groq tokens, more than a day's budget.
   - The 11 Qwen-era ensembles are valid 3-judge verdicts; leave them.
   - Rule changes now reach old verdicts through **`evolvra reaggregate`** (0 API calls), which `cycle` also runs
     on every run.
4. **Leniency mix:** keep it for now. The ceiling rule was built for exactly two lenient judges plus one strict one.
   Point 1 stops the strict judge from steering evolution alone when both others found nothing.
   - Revisit after a week of data. If gpt-oss is still the strictest on about 90% of tasks, the next step is
     per-judge calibration (subtract each judge's mean offset), not dropping it.
5. **Zips:** yes. The mission skill now has a **Machine notes** line in every handoff. Current notes:
   - `Compress-Archive` fails on this PC; in-box .NET `System.IO.Compression.ZipArchive`/`ZipFile` is allowed.
   - PowerShell, not Git Bash.

Also fixed from your report:
- Error rows are now stored even when the coverage guard keeps an older ensemble, so a missing verdict's cause is
  never lost again. A judge that answers later clears its stale error row.
- `scripts/cycle.ps1` sets `PYTHONIOENCODING=utf-8`, so the cp1252 crash you hit cannot happen inside the cycle.

## Requested now (short round)
1. `git pull`; refresh the plugin to **0.3.3** (`claude plugin marketplace update evolvra`,
   `claude plugin update evolvra@evolvra`, restart); tests: **expect 66**; ruff clean.
2. `cd core; uv run evolvra reaggregate`. Report the contested list it prints, then run `uv run evolvra fitness`.
   - Expect content-creator's top failure to show `(contested)` or to change.
   - Commit nothing by hand; the next cycle exports it.
3. Let the scheduled **6 Nov 04:17 AST** run evolve devops-automator. It pulls first, so it uses this code. Next
   session, report:
   - the result: promoted or refused, the delta, and the 4 candidate targets;
   - verdicts and errors per judge in the tournament;
   - OpenRouter requests vs Nemotron verdicts (expect about 1:1);
   - whether the diagnosis file shows any `contested` lines.
4. After that, if OpenRouter has at least 8 requests left: `uv run evolvra score --mission
   20261105-072406-write-a-product-announcement --rescore` (6 fresh calls). Report whether gpt-oss now answers
   by id and whether the "each paragraph" misread is gone.
5. One mission for **backend-architect** (second weakest, 0.863, only 2 tasks), using the Machine notes line in
   the handoff. Then `.\scripts\cycle.ps1`. STATUS as usual.
