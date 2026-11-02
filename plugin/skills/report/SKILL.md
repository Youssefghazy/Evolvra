---
name: report
description: Summarize Evolvra's recent missions and agent performance. Use when the user says "/evolvra:report", "how is the agency doing", or asks which agents are strong or weak.
---

# Evolvra Report

1. Run `evolvra agents` and `evolvra missions --last 10` if the `evolvra` CLI is installed; otherwise read
   `${EVOLVRA_HOME:-~/.evolvra}/missions/*/mission.json` directly.
2. Report, in this order: missions run, pass rate, agents with the most FAIL verdicts, agents never used.
3. Recommend at most one agent to evolve next and say why in one sentence.
Keep it under 15 lines. Numbers go in a small table.
