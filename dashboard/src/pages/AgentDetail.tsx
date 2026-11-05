import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, GitCommitHorizontal, MessageSquareQuote } from "lucide-react";
import { addedLines, description, fmtDate, grade, humanize, pct, signedPct, toneVar, type Data } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { Avatar, Bar, Chip, DivisionChip, Empty, Ring, SectionHeader, Verdict } from "../components/ui";
import Diff from "../components/Diff";

export default function AgentDetail({ data, slug }: { data: Data; slug: string }) {
  const agent = data.agents.find((a) => a.slug === slug);
  const versions = agent?.versions ?? [];
  const [pair, setPair] = useState<[number, number] | null>(null);
  const [showPersona, setShowPersona] = useState(false);
  const critiques = useMemo(() => data.missions.flatMap((m) => m.tasks.filter((t) => t.agent === slug).map((t) => {
    const ens = t.scores.find((s) => s.judge === "ensemble" && s.metric === "rubric:correctness");
    const ev = (ens?.evidence ?? {}) as { critique?: string; failure_class?: string };
    return { m, t, critique: ev.critique, failure: ev.failure_class };
  })), [data, slug]);
  if (!agent) return <Empty title="Unknown agent" hint={slug} />;

  const vb = pair?.[1] ?? versions[versions.length - 1].version;
  const va = pair?.[0] ?? Math.max(1, vb - 1);
  const A = versions.find((v) => v.version === va)!, B = versions.find((v) => v.version === vb)!;
  const evos = data.evolutions.filter((e) => e.agent === slug);
  const g = grade(agent.fitness);
  const learned = versions.length > 1 ? addedLines(versions[versions.length - 2].content, versions[versions.length - 1].content, 6) : [];

  return (
    <div className="space-y-8">
      <a href={href.agents} className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"><ArrowLeft size={14} /> All agents</a>

      <Reveal>
        <Spotlight className="p-6 md:p-8">
          <div className="flex flex-col gap-6 md:flex-row md:items-center">
            <Avatar agent={agent} size={84} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-3xl font-semibold tracking-tight">{agent.name}</h1>
                <DivisionChip division={agent.division} />
                <span className="rounded-md border border-line px-1.5 font-mono text-xs text-muted">v{agent.current_version}</span>
              </div>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink2">{description(agent)}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <Chip>{agent.tasks} tasks graded</Chip>
                <Chip>{versions.length} version{versions.length > 1 ? "s" : ""}</Chip>
                <Chip>{evos.length} evolution run{evos.length === 1 ? "" : "s"}</Chip>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Ring value={agent.fitness} size={104} stroke={8} />
              <div><div className="text-xs text-muted">Fitness</div><div className="font-medium" style={{ color: toneVar[g.tone] }}>{g.label}</div></div>
            </div>
          </div>
        </Spotlight>
      </Reveal>

      <div className="grid gap-5 lg:grid-cols-5">
        <Reveal className="min-w-0 lg:col-span-3">
          <div className="surface h-full p-6">
            <SectionHeader eyebrow="Genealogy" title="Every version, and why it exists" />
            <div className="flex items-center gap-0 overflow-x-auto pb-2">
              {versions.map((v, i) => (
                <div key={v.version} className="flex items-center">
                  {i > 0 && (
                    <motion.div className="h-px w-16 md:w-24" style={{ background: "linear-gradient(90deg, var(--line-strong), var(--good))" }}
                      initial={{ scaleX: 0, originX: 0 }} whileInView={{ scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 0.8 }} />
                  )}
                  <button onClick={() => i > 0 && setPair([versions[i - 1].version, v.version])}
                    className={`min-w-[132px] rounded-xl border p-3 text-left transition-colors ${v.version === vb ? "border-line-strong bg-card-hover" : "border-line bg-card hover:border-line-strong"}`}>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-sm font-semibold">v{v.version}</span>
                      {v.version === agent.current_version && <span className="text-[10px] uppercase tracking-wider text-good">current</span>}
                    </div>
                    <div className="mt-1 text-[11px] text-muted">{v.created_by === "import" ? "original" : "evolved"} · {fmtDate(v.created_at)}</div>
                    <div className="mt-2 font-mono text-lg tnum" style={{ color: toneVar[grade(v.fitness).tone] }}>{pct(v.fitness)}</div>
                    <div className="text-[11px] text-muted">{v.tasks} real task{v.tasks === 1 ? "" : "s"}</div>
                  </button>
                </div>
              ))}
            </div>
            {versions.length > 1 && versions[versions.length - 1].rationale && (
              <p className="mt-4 flex gap-2 text-sm text-ink2"><GitCommitHorizontal size={16} className="mt-0.5 shrink-0 text-muted" />
                {versions[versions.length - 1].rationale}</p>
            )}
            {versions.length === 1 && <p className="mt-4 text-sm text-muted">Still the original. It evolves when it becomes the weakest agent and a rewrite beats it.</p>}
          </div>
        </Reveal>
        <Reveal className="min-w-0 lg:col-span-2" delay={0.06}>
          <div className="surface h-full p-6">
            <SectionHeader eyebrow="Evolution runs" title={`${evos.length} generation${evos.length === 1 ? "" : "s"}`} />
            {evos.length === 0 ? <p className="text-sm text-muted">Never targeted yet.</p> : (
              <ul className="space-y-3">
                {[...evos].reverse().map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-ink2">{fmtDate(e.created_at)}</span>
                    <span className={`font-mono text-xs ${e.winner_version ? "text-good" : "text-muted"}`}>
                      {e.winner_version ? `promoted v${e.winner_version} (${signedPct(e.delta)})` : e.delta == null ? "refused (no fair comparison)" : `refused (${signedPct(e.delta)})`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Reveal>
      </div>

      {learned.length > 0 && (
        <Reveal>
          <div className="surface p-6">
            <SectionHeader eyebrow="What it learned" title="New rules in the latest version" />
            <ul className="grid gap-3 md:grid-cols-2">
              {learned.map((l, i) => (
                <li key={i} className="flex gap-2.5 rounded-xl border border-line bg-card p-3 text-sm text-ink2">
                  <span className="font-mono text-good">+</span>{l}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>
      )}

      <Reveal>
        <div className="surface p-6">
          <SectionHeader eyebrow="Persona" title={versions.length > 1 ? "Exact diff between versions" : "Persona file"}
            action={
              <div className="flex items-center gap-2 text-xs">
                {versions.length > 1 && (
                  <>
                    <select className="rounded-lg border border-line bg-card-solid px-2 py-1" value={va} onChange={(e) => setPair([Number(e.target.value), vb])}>
                      {versions.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                    </select>
                    <span className="text-muted">→</span>
                    <select className="rounded-lg border border-line bg-card-solid px-2 py-1" value={vb} onChange={(e) => setPair([va, Number(e.target.value)])}>
                      {versions.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                    </select>
                  </>
                )}
                <button onClick={() => setShowPersona(!showPersona)} className="rounded-lg border border-line bg-card px-2.5 py-1 text-ink2 hover:text-ink">
                  {showPersona ? "Hide" : "Show"} full file
                </button>
              </div>
            } />
          {versions.length > 1 && A && B && <Diff a={A.content} b={B.content} labelA={`v${A.version}`} labelB={`v${B.version}`} />}
          {(showPersona || versions.length === 1) && (
            <pre className="mt-4 max-h-[520px] overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-bg2 p-4 font-mono text-xs leading-relaxed text-ink2">{B.content}</pre>
          )}
        </div>
      </Reveal>

      <Reveal>
        <div className="surface p-6">
          <SectionHeader eyebrow="Track record" title="What the judges said" />
          {critiques.length === 0 ? <p className="text-sm text-muted">No graded tasks yet.</p> : (
            <ul className="divide-y divide-line">
              {critiques.map(({ m, t, critique, failure }) => (
                <li key={`${m.id}-${t.no}`} className="grid gap-3 py-4 md:grid-cols-[1fr_9rem_6rem] md:items-center">
                  <div className="min-w-0">
                    <a href={href.mission(m.id)} className="line-clamp-1 font-medium hover:text-accent">{t.task}</a>
                    {critique && critique !== "none" && (
                      <p className="mt-1 flex gap-1.5 text-sm text-ink2"><MessageSquareQuote size={14} className="mt-0.5 shrink-0 text-muted" />{critique}</p>
                    )}
                    {failure && failure !== "none" && <div className="mt-1.5"><Chip tone="var(--warn)">{humanize(failure)}</Chip></div>}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted"><Verdict v={t.verdict} /> · {t.attempts} attempt{t.attempts > 1 ? "s" : ""}</div>
                  <div className="flex items-center gap-2"><Bar value={t.fitness} color={toneVar[grade(t.fitness).tone]} /><span className="font-mono text-xs tnum">{pct(t.fitness)}</span></div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Reveal>
    </div>
  );
}
