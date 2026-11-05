import { useMemo, useRef, useState } from "react";
import { motion, useScroll, useTransform } from "motion/react";
import { ChevronDown, GitBranch, ShieldX } from "lucide-react";
import { fmtDate, humanize, pct, signedPct, type Data, type Evolution } from "../data";
import { href } from "../lib/router";
import { NumberTicker, Reveal } from "../components/fx";
import { Avatar, Chip, Empty, SectionHeader } from "../components/ui";

const MARGIN = 0.03;

export default function Evolutions({ data }: { data: Data }) {
  const [agent, setAgent] = useState("all");
  const list = useMemo(() => [...data.evolutions].reverse().filter((e) => agent === "all" || e.agent === agent), [data, agent]);
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 70%", "end 60%"] });
  const scaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);
  if (data.evolutions.length === 0) return <Empty title="No generations yet" hint="The scheduler evolves the weakest agent at most every 12 hours." />;
  const promoted = data.evolutions.filter((e) => e.winner_version != null).length;
  const targets = [...new Set(data.evolutions.map((e) => e.agent))];

  return (
    <div>
      <Reveal><SectionHeader eyebrow="Evolution" title="Every generation, including the ones that lost"
        sub="Refusals are the point: a rewrite must beat the original by at least 3 points on the same held-out tasks, or nothing changes." /></Reveal>
      <Reveal delay={0.04}>
        <div className="mb-8 grid grid-cols-3 gap-3">
          <div className="surface p-4"><div className="text-xs text-muted">Generations</div><div className="mt-1 text-2xl font-semibold"><NumberTicker value={data.evolutions.length} /></div></div>
          <div className="surface p-4"><div className="text-xs text-muted">Promoted</div><div className="mt-1 text-2xl font-semibold text-good"><NumberTicker value={promoted} /></div></div>
          <div className="surface p-4"><div className="text-xs text-muted">Refused</div><div className="mt-1 text-2xl font-semibold"><NumberTicker value={data.evolutions.length - promoted} /></div></div>
        </div>
      </Reveal>
      <div className="mb-6 flex flex-wrap gap-2">
        {["all", ...targets].map((t) => {
          const a = data.agents.find((x) => x.slug === t);
          return (
            <button key={t} onClick={() => setAgent(t)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${agent === t ? "border-line-strong bg-card-hover text-ink" : "border-line text-muted hover:text-ink"}`}>
              {a && <span>{a.emoji}</span>}{a?.name ?? "All agents"}
            </button>
          );
        })}
      </div>
      <div ref={ref} className="relative pl-8 md:pl-10">
        <div className="absolute bottom-0 left-[11px] top-0 w-px bg-line md:left-[15px]" />
        <motion.div className="absolute left-[11px] top-0 w-px origin-top md:left-[15px]"
          style={{ scaleY, height: "100%", background: "linear-gradient(var(--accent), var(--accent-2), var(--accent-3))" }} />
        <div className="space-y-5">
          {list.map((e, i) => <Reveal key={e.id} delay={Math.min(i, 6) * 0.04}><Generation e={e} data={data} /></Reveal>)}
        </div>
      </div>
    </div>
  );
}

function Generation({ e, data }: { e: Evolution; data: Data }) {
  const [open, setOpen] = useState(false);
  const a = data.agents.find((x) => x.slug === e.agent);
  const won = e.winner_version != null;
  const reason = won ? `Won by ${signedPct(e.delta)} on held-out tasks`
    : e.delta == null ? "No candidate finished enough shared tasks for a fair comparison"
      : `Best rewrite ${signedPct(e.delta)}; the gate is +${(MARGIN * 100).toFixed(0)}%`;
  return (
    <div className="relative">
      <span className="absolute -left-[29px] top-6 grid h-4 w-4 place-items-center rounded-full ring-4 ring-bg md:-left-[33px]"
        style={{ background: won ? "var(--good)" : "var(--card-solid)", border: won ? undefined : "1px solid var(--line-strong)", boxShadow: won ? "0 0 18px var(--good)" : undefined }} />
      <div className={won ? "beam" : ""}>
        <div className={won ? "beam-inner p-5" : "surface p-5"}>
          <div className="flex flex-wrap items-center gap-3">
            {a && <Avatar agent={a} size={36} />}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <a href={href.agent(e.agent)} className="font-semibold hover:text-accent">{a?.name ?? e.agent}</a>
                {won ? <Chip tone="var(--good)"><GitBranch size={11} /> v{e.parent_version} → v{e.winner_version}</Chip>
                  : <Chip><ShieldX size={11} /> refused · stays v{e.parent_version}</Chip>}
              </div>
              <div className="mt-0.5 text-xs text-muted">{fmtDate(e.created_at)} · {reason}</div>
            </div>
            <Gate delta={e.delta} won={won} />
          </div>
          {e.candidates.length > 0 && (
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              {e.candidates.map((c) => {
                const best = won && c.paired_delta != null && c.paired_delta === e.delta;
                return (
                  <div key={c.index} className={`rounded-xl border p-3 text-xs ${best ? "border-line-strong bg-card-hover" : "border-line bg-card"}`}>
                    <div className="flex items-center justify-between"><span className="font-mono text-muted">rewrite {c.index}</span>
                      {best && <span className="text-[10px] uppercase tracking-wider text-good">winner</span>}</div>
                    <div className="mt-1 line-clamp-1 font-medium text-ink2" title={c.target}>{humanize(c.target)}</div>
                    <div className="mt-2 flex justify-between font-mono">
                      {c.lint_ok ? <><span className="text-muted">score {pct(c.fitness)}</span><span className={(c.paired_delta ?? 0) >= MARGIN ? "text-good" : "text-muted"}>{signedPct(c.paired_delta)}</span></>
                        : <span className="text-bad">invalid file, not played</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {e.diagnosis && (
            <div className="mt-3">
              <button onClick={() => setOpen(!open)} className="inline-flex items-center gap-1 text-xs text-muted hover:text-ink">
                <ChevronDown size={13} className={`transition-transform ${open ? "rotate-180" : ""}`} /> Diagnosis that drove this generation
              </button>
              {open && <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-line bg-bg2 p-3 font-mono text-[11px] leading-relaxed text-ink2">{e.diagnosis}</pre>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Where the best rewrite landed relative to the +3% gate, on a −10…+20 point scale. */
function Gate({ delta, won }: { delta: number | null; won: boolean }) {
  const lo = -0.1, hi = 0.2;
  const x = (v: number) => `${((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="w-40" title="Best rewrite vs the promotion gate">
      <div className="relative h-5">
        <div className="absolute inset-x-0 top-1/2 h-px bg-line" />
        <div className="absolute top-0 h-5 w-px bg-muted/60" style={{ left: x(0) }} />
        <div className="absolute top-0 h-5 w-px" style={{ left: x(MARGIN), background: "var(--good)" }} />
        {delta != null && <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-4 ring-bg"
          style={{ left: x(delta), background: won ? "var(--good)" : "var(--ink-2)" }} />}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted"><span>0</span><span style={{ color: "var(--good)" }}>gate +3</span></div>
    </div>
  );
}
