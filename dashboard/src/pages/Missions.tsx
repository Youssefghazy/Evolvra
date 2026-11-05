import { useMemo, useState } from "react";
import { ArrowLeft, Check, Gavel, RotateCcw, Search, X } from "lucide-react";
import { fmtDate, grade, humanize, pct, providerName, relTime, toneVar, type Data, type Mission, type Task } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { Avatar, Bar, Chip, Empty, SectionHeader, Verdict } from "../components/ui";

export default function Missions({ data, id }: { data: Data; id?: string }) {
  if (id) {
    const m = data.missions.find((x) => x.id === id);
    return m ? <MissionDetail m={m} data={data} /> : <Empty title="Unknown mission" hint={id} />;
  }
  return <MissionList data={data} />;
}

function avgFitness(m: Mission) {
  const f = m.tasks.map((t) => t.fitness).filter((x): x is number => x != null);
  return f.length ? f.reduce((a, b) => a + b, 0) / f.length : null;
}

function MissionList({ data }: { data: Data }) {
  const [q, setQ] = useState("");
  const list = useMemo(() => data.missions.filter((m) => m.brief.toLowerCase().includes(q.toLowerCase())), [data, q]);
  if (data.missions.length === 0) return <Empty title="No missions yet" hint="Run /evolvra:mission in Claude Code; the next cycle publishes it here." />;
  const retried = data.missions.filter((m) => m.tasks.some((t) => t.attempts > 1)).length;
  return (
    <div>
      <Reveal><SectionHeader eyebrow="Missions" title={`${data.missions.length} missions, every task independently checked`}
        sub={`A builder agent does the work, a QA agent verifies it, and three judges grade both. ${retried} mission${retried === 1 ? "" : "s"} needed a retry after QA pushed back.`} /></Reveal>
      <Reveal delay={0.04}>
        <label className="mb-5 flex items-center gap-2 rounded-xl border border-line bg-card px-3 py-2 text-sm">
          <Search size={15} className="text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter missions…" className="w-full bg-transparent outline-none placeholder:text-muted" />
        </label>
      </Reveal>
      <div className="space-y-3">
        {list.map((m, i) => {
          const avg = avgFitness(m);
          const retries = m.tasks.reduce((n, t) => n + Math.max(0, t.attempts - 1), 0);
          return (
            <Reveal key={m.id} delay={Math.min(i, 8) * 0.03}>
              <Spotlight href={href.mission(m.id)} className="block px-5 py-4">
                <div className="grid items-center gap-4 md:grid-cols-[1fr_auto_7rem]">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-xs text-muted">
                      <Verdict v={m.status} compact /><span className="uppercase tracking-wider">{m.mode}</span><span>·</span><span>{relTime(m.started_at)}</span>
                      {retries > 0 && <span className="inline-flex items-center gap-1 text-warn"><RotateCcw size={11} />{retries} retry</span>}
                    </div>
                    <p className="mt-1.5 line-clamp-1 font-medium">{m.brief}</p>
                  </div>
                  <div className="flex -space-x-2">
                    {m.tasks.map((t) => { const a = data.agents.find((x) => x.slug === t.agent); return a ? <Avatar key={t.no} agent={a} size={30} /> : null; })}
                  </div>
                  <div className="flex items-center gap-2"><Bar value={avg} color={toneVar[grade(avg).tone]} /><span className="font-mono text-xs tnum">{pct(avg)}</span></div>
                </div>
              </Spotlight>
            </Reveal>
          );
        })}
      </div>
    </div>
  );
}

function MissionDetail({ m, data }: { m: Mission; data: Data }) {
  return (
    <div className="space-y-6">
      <a href={href.missions} className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"><ArrowLeft size={14} /> All missions</a>
      <Reveal>
        <div className="surface p-6 md:p-8">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
            <Verdict v={m.status} /><span>·</span><span className="uppercase tracking-wider">{m.mode}</span><span>·</span>
            <span>{fmtDate(m.started_at)} → {fmtDate(m.finished_at)}</span>
          </div>
          <h1 className="mt-3 text-2xl font-semibold leading-snug tracking-tight md:text-3xl">{m.brief}</h1>
          {m.summary && <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink2">{m.summary}</p>}
          <div className="mt-6 flex flex-wrap items-center gap-3">
            {m.tasks.map((t, i) => {
              const a = data.agents.find((x) => x.slug === t.agent);
              return (
                <div key={t.no} className="flex items-center gap-3">
                  {i > 0 && <span className="h-px w-8 bg-line-strong" />}
                  <div className="flex items-center gap-2 rounded-full border border-line bg-card py-1 pl-1 pr-3 text-sm">
                    {a && <Avatar agent={a} size={26} />}<span>{a?.name ?? t.agent}</span><Verdict v={t.verdict} compact />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </Reveal>
      {m.tasks.map((t, i) => <Reveal key={t.no} delay={i * 0.05}><TaskCard t={t} data={data} /></Reveal>)}
    </div>
  );
}

const RUBRIC = ["correctness", "completeness", "quality", "evidence"] as const;

function TaskCard({ t, data }: { t: Task; data: Data }) {
  const a = data.agents.find((x) => x.slug === t.agent);
  const ens = Object.fromEntries(t.scores.filter((s) => s.judge === "ensemble").map((s) => [s.metric.replace("rubric:", ""), s]));
  const judges = [...new Set(t.scores.filter((s) => !["ensemble", "deterministic"].includes(s.judge) && s.metric.startsWith("rubric:")).map((s) => s.judge))];
  const det = t.scores.filter((s) => s.judge === "deterministic");
  const ev = (ens.correctness?.evidence ?? {}) as { critique?: string; failure_class?: string };
  const g = grade(t.fitness);
  return (
    <div className="surface overflow-hidden">
      <div className="flex flex-wrap items-center gap-4 border-b border-line p-5 md:p-6">
        {a && <Avatar agent={a} size={44} />}
        <div className="min-w-0 flex-1">
          <div className="text-xs text-muted">Task {t.no} · <a className="hover:text-ink" href={href.agent(t.agent)}>{a?.name ?? t.agent}</a></div>
          <div className="mt-0.5 font-medium">{t.task}</div>
        </div>
        <div className="text-right">
          <div className="font-mono text-2xl font-semibold tnum" style={{ color: toneVar[g.tone] }}>{pct(t.fitness)}</div>
          <div className="text-[11px] text-muted">fitness · {g.label.toLowerCase()}</div>
        </div>
      </div>
      <div className="grid gap-6 p-5 md:p-6 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-6">
          {t.acceptance.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Acceptance criteria</div>
              <ul className="space-y-1.5 text-sm text-ink2">{t.acceptance.map((c, i) => <li key={i} className="flex gap-2"><span className="text-muted">•</span>{c}</li>)}</ul>
            </div>
          )}
          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Attempts</div>
            <ol className="space-y-3 border-l border-line pl-4">
              {t.attempt_log.map((at) => (
                <li key={at.n} className="relative text-sm">
                  <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full ring-4 ring-bg"
                    style={{ background: at.verdict === "PASS" ? "var(--good)" : at.verdict ? "var(--warn)" : "var(--muted)" }} />
                  <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs text-muted">#{at.n}</span><Verdict v={at.verdict} />
                    {at.reopened_by_qa && <Chip tone="var(--warn)">reopened by QA</Chip>}
                    {at.caused_by_builder && <Chip>re-run after builder fix</Chip>}
                  </div>
                  {(at.feedback || at.evidence) && <Clamp text={(at.feedback ?? at.evidence) as string} />}
                </li>
              ))}
            </ol>
          </div>
          {det.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">Automatic checks</div>
              <ul className="grid grid-cols-2 gap-2 text-xs">
                {det.map((d) => (
                  <li key={d.metric} className="flex items-center gap-1.5 text-ink2">
                    {d.value >= 0.99 ? <Check size={13} className="text-good" /> : d.value <= 0.01 ? <X size={13} className="text-bad" /> : <span className="font-mono text-warn">{pct(d.value)}</span>}
                    {humanize(d.metric.replace("det:", ""))}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted"><Gavel size={13} /> The judges</div>
          {judges.length === 0 ? <p className="text-sm text-muted">Not graded yet.</p> : (
            <>
              <div className="rounded-xl border border-line-strong bg-card-hover p-4">
                <div className="mb-3 flex items-center justify-between text-sm"><span className="font-medium">Ensemble verdict</span>
                  {ev.failure_class && ev.failure_class !== "none" && <Chip tone="var(--warn)">{humanize(ev.failure_class)}</Chip>}</div>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2.5">
                  {RUBRIC.map((k) => (
                    <div key={k}>
                      <div className="flex justify-between text-xs"><span className="text-ink2">{humanize(k)}</span><span className="font-mono tnum">{pct(ens[k]?.value)}</span></div>
                      <Bar value={ens[k]?.value ?? null} height={5} className="mt-1" color={toneVar[grade(ens[k]?.value).tone]} />
                    </div>
                  ))}
                </div>
                {ev.critique && ev.critique !== "none" && <p className="mt-3 border-t border-line pt-3 text-sm leading-relaxed text-ink2">“{ev.critique}”</p>}
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {judges.map((j) => {
                  const rows = t.scores.filter((s) => s.judge === j);
                  const err = rows.find((s) => s.metric === "rubric:error");
                  const corr = rows.find((s) => s.metric === "rubric:correctness");
                  const { provider, model } = providerName(j);
                  const crit = ((corr?.evidence ?? err?.evidence ?? {}) as { critique?: string }).critique;
                  return (
                    <div key={j} className="rounded-xl border border-line bg-card p-3">
                      <div className="truncate text-xs font-medium" title={j}>{model}</div>
                      <div className="text-[10px] uppercase tracking-wider text-muted">{provider}</div>
                      {err && !corr ? <div className="mt-2 text-xs text-muted">No verdict (provider error)</div> : (
                        <div className="mt-2 space-y-1">
                          {RUBRIC.map((k) => {
                            const s = rows.find((r) => r.metric === `rubric:${k}`);
                            return (
                              <div key={k} className="grid grid-cols-[2.2rem_1fr_1.6rem] items-center gap-2" title={humanize(k)}>
                                <span className="text-[10px] text-muted">{k.slice(0, 4)}</span><Bar value={s?.value ?? null} height={3} />
                                <span className="text-right font-mono text-[10px] text-muted">{s ? Math.round(s.value * 100) : "–"}</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                      {crit && crit !== "none" && <p className="mt-2 line-clamp-3 text-[11px] leading-snug text-muted" title={crit}>{crit}</p>}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Clamp({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 220;
  return (
    <div className="mt-1">
      <p className={`text-xs leading-relaxed text-ink2 ${!open && long ? "line-clamp-3" : ""}`}>{text}</p>
      {long && <button onClick={() => setOpen(!open)} className="mt-0.5 text-[11px] text-accent hover:underline">{open ? "Show less" : "Show more"}</button>}
    </div>
  );
}
