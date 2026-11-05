import { useMemo } from "react";
import { Activity, Dna, Download, RotateCcw, Rocket, Trophy } from "lucide-react";
import { grade, humanize, pct, providerName, relTime, signedPct, toneVar, type Data } from "../data";
import { href } from "../lib/router";
import { NumberTicker, Reveal, Spotlight } from "../components/fx";
import { AreaChart, Sparkline, type Point } from "../components/charts";
import { Avatar, Bar, Chip, SectionHeader } from "../components/ui";

const avg = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

export default function Control({ data }: { data: Data }) {
  const m = useMemo(() => {
    const missions = [...data.missions].sort((a, b) => a.started_at.localeCompare(b.started_at));
    const quality = missions.map((x) => avg(x.tasks.map((t) => t.fitness).filter((f): f is number => f != null)));
    const series: Point[] = missions.flatMap((x, i) => quality[i] == null ? [] : [{
      x: i, y: quality[i]!, label: x.brief,
      sub: `${new Date(x.started_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} · ${x.tasks.length} tasks`,
    }]);
    const q = quality.filter((v): v is number => v != null);
    const recent = avg(q.slice(-5)), prior = avg(q.slice(-10, -5));
    const tasks = missions.flatMap((x) => x.tasks);
    let firstTry = 0, seen = 0;
    const firstTrySeries = tasks.map((t) => { seen++; if (t.attempts === 1 && t.verdict === "PASS") firstTry++; return firstTry / seen; });
    const cumulative = missions.map((_, i) => i + 1);
    const last24 = missions.filter((x) => new Date(data.summary.generated_at).getTime() - new Date(x.started_at).getTime() < 86400000).length;
    const judges = new Map<string, { ok: number; err: number }>();
    for (const t of tasks) for (const s of t.scores) {
      if (["ensemble", "deterministic"].includes(s.judge)) continue;
      const j = judges.get(s.judge) ?? { ok: 0, err: 0 };
      if (s.metric === "rubric:correctness") j.ok++;
      if (s.metric === "rubric:error") j.err++;
      judges.set(s.judge, j);
    }
    const events: { at: string; icon: typeof Rocket; tone: string; text: string; to: string }[] = [];
    for (const x of missions) {
      events.push({ at: x.started_at, icon: Rocket, tone: "var(--accent)", text: `Mission: ${x.brief}`, to: href.mission(x.id) });
      for (const t of x.tasks) for (const a of t.attempt_log) if (a.reopened_by_qa)
        events.push({ at: a.finished_at ?? a.started_at, icon: RotateCcw, tone: "var(--warn)", text: `QA sent ${humanize(t.agent)}'s work back`, to: href.mission(x.id) });
    }
    for (const e of data.evolutions) events.push({
      at: e.created_at, icon: e.winner_version ? Trophy : Dna, tone: e.winner_version ? "var(--good)" : "var(--muted)",
      text: e.winner_version ? `${humanize(e.agent)} evolved to v${e.winner_version} (${signedPct(e.delta)})` : `${humanize(e.agent)} generation refused`,
      to: href.evolutions,
    });
    events.sort((a, b) => b.at.localeCompare(a.at));
    return { series, recent, prior, q, tasks, firstTry, firstTrySeries, cumulative, last24, judges: [...judges.entries()], events };
  }, [data]);

  const promoted = data.evolutions.filter((e) => e.winner_version != null).length;
  const promoRate = data.evolutions.length ? promoted / data.evolutions.length : 0;
  const calls = data.summary.providers.reduce((n, p) => n + p.requests, 0);
  const tokens = data.summary.providers.reduce((n, p) => n + p.tokens, 0);
  const maxJudge = Math.max(1, ...m.judges.map(([, v]) => v.ok + v.err));
  const agents = [...data.agents].sort((a, b) => (b.fitness ?? -1) - (a.fitness ?? -1));

  return (
    <div className="space-y-6">
      <Reveal>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted">Control room</div>
            <h1 className="mt-1.5 text-2xl font-semibold tracking-tight md:text-3xl">How the agency is performing</h1>
            <p className="mt-1 text-sm text-ink2">All {data.summary.missions} missions · data refreshed {relTime(data.summary.generated_at)} by the scheduler</p>
          </div>
          <div className="flex items-center gap-2">
            <Chip tone="var(--good)">$0.00 spent</Chip>
            <a href={`${import.meta.env.BASE_URL}data/missions.json`} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-ink2 hover:text-ink">
              <Download size={13} /> Raw data
            </a>
          </div>
        </div>
      </Reveal>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi i={0} label="Mission quality" sub="avg fitness, last 5 missions" value={m.recent != null ? Math.round(m.recent * 100) : 0} suffix="%"
          delta={m.recent != null && m.prior != null ? m.recent - m.prior : null} deltaNote="vs the 5 before" spark={m.q} />
        <Kpi i={1} label="Missions run" sub={`${m.last24} in the last 24 h`} value={data.summary.missions} spark={m.cumulative} />
        <Kpi i={2} label="First-try pass rate" sub={`${m.firstTry} of ${m.tasks.length} tasks passed on attempt 1`}
          value={Math.round((m.firstTry / Math.max(1, m.tasks.length)) * 100)} suffix="%" spark={m.firstTrySeries} />
        <Reveal delay={0.18}>
          <Spotlight className="h-full p-5">
            <div className="text-xs text-muted">Promotion rate</div>
            <div className="mt-2 flex items-center gap-4">
              <div className="text-3xl font-semibold tracking-tight"><NumberTicker value={Math.round(promoRate * 100)} suffix="%" /></div>
              <div className="flex-1"><Bar value={promoRate} color="var(--good)" height={6} /></div>
            </div>
            <div className="mt-2 text-xs text-muted">{promoted} promoted of {data.evolutions.length} generations. Strict by design: the gate is +3 points.</div>
          </Spotlight>
        </Reveal>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Reveal className="min-w-0 lg:col-span-2">
          <div className="surface p-5 md:p-6">
            <SectionHeader eyebrow="Quality over time" title="Average fitness per mission" sub="Missions in the order they ran; the axis starts at 70 because every score sits above it. Hover a point to see the mission." />
            <AreaChart points={m.series} yMin={0.7} refLine={{ y: 0.9, label: "strong · 90" }} />
          </div>
        </Reveal>
        <Reveal className="min-w-0" delay={0.06}>
          <div className="surface h-full p-5 md:p-6">
            <SectionHeader eyebrow="Judges" title="Who answered" />
            <div className="mb-4 flex items-center gap-4 text-[11px] text-muted">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: "var(--series-1)" }} />verdicts</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: "var(--series-muted)" }} />errors</span>
            </div>
            <ul className="space-y-4">
              {m.judges.sort((a, b) => b[1].ok - a[1].ok).map(([j, v]) => {
                const { provider, model } = providerName(j);
                const rate = v.ok / Math.max(1, v.ok + v.err);
                return (
                  <li key={j} title={`${v.ok} verdicts, ${v.err} errors`}>
                    <div className="flex items-baseline justify-between text-sm">
                      <span className="truncate"><span className="text-ink">{model}</span> <span className="text-[11px] uppercase tracking-wider text-muted">{provider}</span></span>
                      <span className="font-mono text-xs tnum text-ink2">{Math.round(rate * 100)}%</span>
                    </div>
                    <div className="mt-1.5 flex h-2 gap-[2px] overflow-hidden rounded-full">
                      <div className="h-full rounded-l-full" style={{ width: `${(v.ok / maxJudge) * 100}%`, background: "var(--series-1)" }} />
                      {v.err > 0 && <div className="h-full rounded-r-full" style={{ width: `${(v.err / maxJudge) * 100}%`, background: "var(--series-muted)" }} />}
                    </div>
                  </li>
                );
              })}
            </ul>
            <div className="mt-6 border-t border-line pt-4">
              <div className="text-xs text-muted">Free-tier usage</div>
              <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                {data.summary.providers.map((p) => (
                  <div key={p.provider} className="rounded-xl border border-line bg-card p-2">
                    <div className="font-mono text-sm font-semibold tnum">{p.requests}</div>
                    <div className="text-[10px] uppercase tracking-wider text-muted">{p.provider}</div>
                  </div>
                ))}
              </div>
              <div className="mt-2 text-[11px] text-muted">{calls} requests · {(tokens / 1000).toFixed(0)}k tokens · {"$0.00"}</div>
            </div>
          </div>
        </Reveal>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Reveal className="min-w-0 lg:col-span-2">
          <div className="surface overflow-hidden">
            <div className="px-5 pt-5 md:px-6"><SectionHeader eyebrow="Roster" title="Agents" /></div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-y border-line text-left text-[11px] uppercase tracking-wider text-muted">
                    <th className="px-5 py-2.5 font-medium md:px-6">Agent</th><th className="py-2.5 font-medium">Version</th>
                    <th className="py-2.5 font-medium">Tasks</th><th className="py-2.5 font-medium">Fitness</th><th className="py-2.5 pr-5 font-medium md:pr-6">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {agents.map((a) => {
                    const g = grade(a.fitness);
                    const prev = a.versions.length > 1 ? a.versions[a.versions.length - 2] : null;
                    return (
                      <tr key={a.slug} className="border-b border-line last:border-0 hover:bg-card-hover">
                        <td className="px-5 py-3 md:px-6">
                          <a href={href.agent(a.slug)} className="flex items-center gap-3"><Avatar agent={a} size={30} />
                            <span><span className="block font-medium">{a.name}</span><span className="block text-xs capitalize text-muted">{a.division}</span></span></a>
                        </td>
                        <td className="py-3"><span className="rounded-md border border-line px-1.5 font-mono text-xs">v{a.current_version}</span>
                          {prev && prev.fitness != null && a.fitness != null && <span className="ml-2 font-mono text-xs text-good">{signedPct(a.fitness - prev.fitness)}</span>}</td>
                        <td className="py-3 font-mono text-xs tnum text-ink2">{a.tasks}</td>
                        <td className="py-3"><div className="flex w-36 items-center gap-2"><Bar value={a.fitness} color={toneVar[g.tone]} /><span className="font-mono text-xs tnum">{pct(a.fitness)}</span></div></td>
                        <td className="py-3 pr-5 md:pr-6"><Chip tone={toneVar[g.tone]}>{g.label}</Chip></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </Reveal>
        <Reveal className="min-w-0" delay={0.06}>
          <div className="surface h-full p-5 md:p-6">
            <SectionHeader eyebrow="Activity" title="Latest events" />
            <ol className="relative space-y-4 border-l border-line pl-5">
              {m.events.slice(0, 9).map((e, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[31px] grid h-5 w-5 place-items-center rounded-full border border-line bg-card-solid"><e.icon size={11} style={{ color: e.tone }} /></span>
                  <a href={e.to} className="line-clamp-2 text-sm text-ink2 hover:text-ink">{e.text}</a>
                  <div className="text-[11px] text-muted">{relTime(e.at)}</div>
                </li>
              ))}
            </ol>
            <div className="mt-4 flex items-center gap-1.5 text-[11px] text-muted"><Activity size={12} /> refreshed every 6 h by the scheduler</div>
          </div>
        </Reveal>
      </div>
    </div>
  );
}

function Kpi({ i, label, sub, value, suffix = "", delta, deltaNote, spark }: {
  i: number; label: string; sub: string; value: number; suffix?: string; delta?: number | null; deltaNote?: string; spark: number[];
}) {
  return (
    <Reveal delay={i * 0.06}>
      <Spotlight className="h-full p-5">
        <div className="flex items-center justify-between text-xs text-muted"><span>{label}</span>
          {delta != null && <span className="rounded-full px-1.5 py-0.5 font-mono text-[11px]" title={deltaNote}
            style={{ color: delta >= 0 ? "var(--good)" : "var(--bad)", background: `color-mix(in srgb, ${delta >= 0 ? "var(--good)" : "var(--bad)"} 12%, transparent)` }}>
            {delta >= 0 ? "▲" : "▼"} {Math.abs(delta * 100).toFixed(1)}</span>}
        </div>
        <div className="mt-2 text-3xl font-semibold tracking-tight"><NumberTicker value={value} suffix={suffix} /></div>
        <div className="mt-3"><Sparkline values={spark} /></div>
        <div className="mt-2 text-xs text-muted">{sub}</div>
      </Spotlight>
    </Reveal>
  );
}
