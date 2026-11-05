import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, GitCommitHorizontal, MessageSquareQuote } from "lucide-react";
import { addedLines, description, fmtDate, grade, humanize, pct, signedPct, toneVar, type Data } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { Avatar, Bar, Chip, DivisionChip, Empty, Ring, SectionHeader, Verdict } from "../components/ui";
import Diff from "../components/Diff";
import AgentPassport from "../components/AgentPassport";
import { useIsPhone } from "../lib/media";

export default function AgentDetail({ data, slug }: { data: Data; slug: string }) {
  const phone = useIsPhone();
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
    <div className="space-y-5 md:space-y-8">
      <a href={href.agents} className="-my-2 -ml-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-2 text-sm text-muted hover:text-ink"><ArrowLeft size={14} /> All agents</a>

      <div className="grid items-center gap-6 lg:grid-cols-[1fr_auto]">
      <Reveal>
        <Spotlight className="p-5 md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:gap-6">
            <div className="flex items-center gap-4 md:contents">
              <Avatar agent={agent} size={phone ? 60 : 84} />
              {/* phone: name sits beside the avatar; desktop: in the main column */}
              <div className="min-w-0 md:hidden">
                <h1 className="text-2xl font-semibold leading-tight tracking-tight">{agent.name}</h1>
                <div className="mt-1.5 flex items-center gap-2"><DivisionChip division={agent.division} />
                  <span className="rounded-md border border-line px-1.5 font-mono text-xs text-muted">v{agent.current_version}</span></div>
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <div className="hidden flex-wrap items-center gap-2 md:flex">
                <h1 className="text-3xl font-semibold tracking-tight">{agent.name}</h1>
                <DivisionChip division={agent.division} />
                <span className="rounded-md border border-line px-1.5 font-mono text-xs text-muted">v{agent.current_version}</span>
              </div>
              <p className="max-w-2xl text-sm leading-relaxed text-ink2 md:mt-3">{description(agent)}</p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <Chip>{agent.tasks} tasks graded</Chip>
                <Chip>{versions.length} version{versions.length > 1 ? "s" : ""}</Chip>
                <Chip>{evos.length} evolution run{evos.length === 1 ? "" : "s"}</Chip>
              </div>
            </div>
            <div className="flex items-center gap-4 border-t border-line pt-4 md:border-0 md:pt-0">
              <Ring value={agent.fitness} size={phone ? 64 : 104} stroke={phone ? 6 : 8} />
              <div><div className="text-xs text-muted">Fitness</div><div className="font-medium" style={{ color: toneVar[g.tone] }}>{g.label}</div></div>
            </div>
          </div>
        </Spotlight>
      </Reveal>
      <Reveal delay={0.1} className="hidden justify-center lg:flex"><AgentPassport agent={agent} /></Reveal>
      </div>

      <div className="grid gap-5 lg:grid-cols-5">
        <Reveal className="min-w-0 lg:col-span-3">
          <div className="surface h-full p-5 md:p-6">
            <SectionHeader eyebrow="Genealogy" title="Every version, and why it exists" />
            {/* phone: versions stack top to bottom; desktop: left to right */}
            <div className="flex flex-col md:flex-row md:items-center md:overflow-x-auto md:pb-2">
              {versions.map((v, i) => (
                <div key={v.version} className="flex flex-col md:flex-row md:items-center">
                  {i > 0 && (
                    <motion.div className="ml-6 h-5 w-px md:ml-0 md:h-px md:w-24"
                      style={{ background: phone ? "linear-gradient(var(--line-strong), var(--good))" : "linear-gradient(90deg, var(--line-strong), var(--good))", originX: 0, originY: 0 }}
                      initial={phone ? { scaleY: 0 } : { scaleX: 0 }} whileInView={phone ? { scaleY: 1 } : { scaleX: 1 }} viewport={{ once: true }} transition={{ duration: 0.8 }} />
                  )}
                  <button onClick={() => i > 0 && setPair([versions[i - 1].version, v.version])}
                    className={`w-full rounded-xl border p-3 text-left transition-colors md:w-auto md:min-w-[132px] ${v.version === vb ? "border-line-strong bg-card-hover" : "border-line bg-card hover:border-line-strong"}`}>
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
          <div className="surface h-full p-5 md:p-6">
            <SectionHeader eyebrow="Evolution runs" title={`${evos.length} generation${evos.length === 1 ? "" : "s"}`} />
            {evos.length === 0 ? <p className="text-sm text-muted">Never targeted yet.</p> : (
              <ul className="space-y-3">
                {[...evos].reverse().map((e) => (
                  <li key={e.id} className="flex flex-wrap items-center justify-between gap-x-3 gap-y-0.5 text-sm">
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
          <div className="surface p-5 md:p-6">
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
        <div className="surface p-5 md:p-6">
          <SectionHeader eyebrow="Persona" title={versions.length > 1 ? "Exact diff between versions" : "Persona file"} />
          {(
              <div className="-mt-1 mb-4 flex flex-wrap items-center gap-2 text-xs">
                {versions.length > 1 && (
                  <>
                    <select aria-label="From version" className="h-9 rounded-lg border border-line bg-card-solid px-2 text-base md:h-auto md:py-1 md:text-xs" value={va} onChange={(e) => setPair([Number(e.target.value), vb])}>
                      {versions.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                    </select>
                    <span className="text-muted">→</span>
                    <select aria-label="To version" className="h-9 rounded-lg border border-line bg-card-solid px-2 text-base md:h-auto md:py-1 md:text-xs" value={vb} onChange={(e) => setPair([va, Number(e.target.value)])}>
                      {versions.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                    </select>
                  </>
                )}
                <button onClick={() => setShowPersona(!showPersona)} className="ml-auto h-9 rounded-lg border border-line bg-card px-3 text-ink2 transition-colors hover:border-line-strong hover:text-ink md:h-auto md:py-1">
                  {showPersona ? "Hide" : "Show"} full file
                </button>
              </div>
          )}
          {versions.length > 1 && A && B && <Diff a={A.content} b={B.content} labelA={`v${A.version}`} labelB={`v${B.version}`} />}
          {(showPersona || versions.length === 1) && (
            <pre className="mt-4 max-h-[520px] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-line bg-bg2 p-3 font-mono text-[11px] leading-relaxed text-ink2 md:p-4 md:text-xs">{B.content}</pre>
          )}
        </div>
      </Reveal>

      <Reveal>
        <div className="surface p-5 md:p-6">
          <SectionHeader eyebrow="Track record" title="What the judges said" />
          {critiques.length === 0 ? <p className="text-sm text-muted">No graded tasks yet.</p> : (
            <ul className="divide-y divide-line">
              {critiques.map(({ m, t, critique, failure }) => (
                <li key={`${m.id}-${t.no}`} className="grid gap-3 py-4 md:grid-cols-[1fr_9rem_6rem] md:items-center">
                  <div className="min-w-0">
                    <a href={href.mission(m.id)} className="line-clamp-2 font-medium hover:text-accent md:line-clamp-1">{t.task}</a>
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
