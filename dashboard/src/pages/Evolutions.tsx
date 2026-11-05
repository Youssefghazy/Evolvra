import { useMemo, useRef, useState } from "react";
import { motion, type MotionValue, useMotionValue, useMotionValueEvent, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { ChevronDown, GitBranch, ShieldX } from "lucide-react";
import { fmtDate, humanize, pct, signedPct, type Data, type Evolution } from "../data";
import { href } from "../lib/router";
import { coarsePointer } from "../lib/media";
import { NumberTicker, Reveal } from "../components/fx";
import { Avatar, Chip, Empty, SectionHeader } from "../components/ui";

const MARGIN = 0.03;

export default function Evolutions({ data }: { data: Data }) {
  const [agent, setAgent] = useState("all");
  const list = useMemo(() => [...data.evolutions].reverse().filter((e) => agent === "all" || e.agent === agent), [data, agent]);
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  // The comet rides a fixed reading line (55% down the viewport), so it reaches each circle exactly
  // when that circle lights up. Near the end of the page the line can no longer reach the last
  // generations, so `ramp` eases everything to "done" over the final 320 px of scroll.
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 55%", "end 55%"] });
  const { scrollY } = useScroll();
  const ramp = useTransform(scrollY, (y) => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    return max <= 0 ? 1 : Math.min(1, Math.max(0, 1 - (max - y) / 320));
  });
  const reached = useTransform([scrollYProgress, ramp], ([a, r]: number[]) => a + (1 - a) * r);
  // Spring-smoothed so the comet glides between wheel ticks instead of jumping.
  const smooth = useSpring(reached, { stiffness: 140, damping: 26, mass: 0.4, restDelta: 0.0005 });
  const full = useMotionValue(1);
  const progress = reduce ? full : smooth;
  const top = useTransform(progress, (v) => `${v * 100}%`);
  const headOpacity = useTransform(progress, [0, 0.015, 0.985, 1], [0, 1, 1, 0]);
  if (data.evolutions.length === 0) return <Empty title="No generations yet" hint="The scheduler evolves the weakest agent at most every 12 hours." />;
  const promoted = data.evolutions.filter((e) => e.winner_version != null).length;
  const targets = [...new Set(data.evolutions.map((e) => e.agent))];

  return (
    <div>
      <Reveal><SectionHeader eyebrow="Evolution" title="Every generation, including the ones that lost"
        sub="Refusals are the point: a rewrite must beat the original by at least 3 points on the same held-out tasks, or nothing changes." /></Reveal>
      <Reveal delay={0.04}>
        <div className="mb-6 grid grid-cols-3 gap-2 sm:mb-8 sm:gap-3">
          <div className="surface p-4"><div className="text-xs text-muted">Generations</div><div className="mt-1 text-2xl font-semibold"><NumberTicker value={data.evolutions.length} /></div></div>
          <div className="surface p-4"><div className="text-xs text-muted">Promoted</div><div className="mt-1 text-2xl font-semibold text-good"><NumberTicker value={promoted} /></div></div>
          <div className="surface p-4"><div className="text-xs text-muted">Refused</div><div className="mt-1 text-2xl font-semibold"><NumberTicker value={data.evolutions.length - promoted} /></div></div>
        </div>
      </Reveal>
      <div className="no-scrollbar -mx-4 mb-6 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
        {["all", ...targets].map((t) => {
          const a = data.agents.find((x) => x.slug === t);
          return (
            <button key={t} onClick={() => setAgent(t)}
              className={`inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-3 text-xs transition-colors sm:h-auto sm:py-1.5 ${agent === t ? "border-line-strong bg-card-hover text-ink" : "border-line text-muted hover:text-ink"}`}>
              {a && <Avatar agent={a} size={18} />}{a?.name ?? "All agents"}
            </button>
          );
        })}
      </div>
      <div ref={ref} className="relative pl-8 md:pl-10">
        {/* track, scroll-scrubbed fill, and the comet head that rides the fill's leading edge */}
        <div className="absolute bottom-0 left-[11px] top-0 w-px bg-line md:left-[15px]" />
        <motion.div className="absolute left-[11px] top-0 w-px origin-top md:left-[15px]"
          style={{ scaleY: progress, height: "100%", background: "linear-gradient(var(--accent), var(--accent-2), var(--accent-3))" }} />
        <motion.div aria-hidden className="pointer-events-none absolute left-[11.5px] z-10 md:left-[15.5px]" style={{ top, opacity: headOpacity }}>
          <span className="absolute bottom-0 left-0 h-24 w-[3px] -translate-x-1/2 rounded-full"
            style={{ background: "linear-gradient(transparent, var(--accent))", filter: "blur(0.5px)" }} />
          <span className="absolute left-0 top-0 h-8 w-8 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ background: "radial-gradient(circle, var(--glow), transparent 70%)" }} />
          <span className="absolute left-0 top-0 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
            style={{ background: "var(--ink)", boxShadow: "0 0 0 2px var(--accent), 0 0 16px 4px var(--accent)" }} />
        </motion.div>
        <div className="space-y-5">
          {list.map((e) => <Generation key={e.id} e={e} data={data} ramp={ramp} />)}
        </div>
      </div>
    </div>
  );
}

function Generation({ e, data, ramp }: { e: Evolution; data: Data; ramp: MotionValue<number> }) {
  const [open, setOpen] = useState(false);
  const a = data.agents.find((x) => x.slug === e.agent);
  const won = e.winner_version != null;
  const tone = won ? "var(--good)" : "var(--accent)";

  // Each generation lights up as the comet reaches it: 0 while it is below the fold line, 1 once its
  // node has crossed it. The same value drives the node, the connector and the card.
  const reduce = useReducedMotion();
  const nodeRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: nodeRef, offset: ["start 72%", "start 52%"] });
  const reached = useTransform([scrollYProgress, ramp], ([a, r]: number[]) => a + (1 - a) * r);
  const eased = useSpring(reached, { stiffness: 160, damping: 24, mass: 0.4 });
  const one = useMotionValue(1);
  const p = reduce ? one : eased;
  const fillScale = useTransform(p, [0, 1], [0.2, 1]);
  const nodeScale = useTransform(p, [0, 0.85, 1], [0.8, 1.18, 1]);
  // phones: lighter dimming, no blur filter (it is expensive to repaint while scrolling on mobile GPUs)
  const cardOpacity = useTransform(p, [0, 1], [coarsePointer ? 0.55 : 0.42, 1]);
  // phones slide up instead of sideways, so a card never pokes past the right edge of a narrow screen
  const cardX = useTransform(p, [0, 1], [coarsePointer ? 0 : 18, 0]);
  const cardY = useTransform(p, [0, 1], [coarsePointer ? 14 : 0, 0]);
  const cardBlur = useTransform(p, [0, 1], coarsePointer ? ["none", "none"] : ["blur(1px)", "blur(0px)"]);
  const [lit, setLit] = useState(false);
  useMotionValueEvent(reached, "change", (v) => { if (v >= 0.98 !== lit) setLit(v >= 0.98); });
  const reason = won ? `Won by ${signedPct(e.delta)} on held-out tasks`
    : e.delta == null ? "No candidate finished enough shared tasks for a fair comparison"
      : `Best rewrite ${signedPct(e.delta)}; the gate is +${(MARGIN * 100).toFixed(0)}%`;
  return (
    <div ref={nodeRef} className="relative">
      {/* node: hollow ring that fills with the generation's color, pulses once when the comet arrives */}
      <motion.span className="absolute -left-[29px] top-6 z-20 grid h-4 w-4 place-items-center rounded-full ring-4 ring-bg md:-left-[33px]"
        style={{ scale: nodeScale, background: "var(--card-solid)", border: "1px solid var(--line-strong)" }}>
        <motion.span className="absolute inset-[-1px] rounded-full" style={{ scale: fillScale, opacity: p, background: tone,
          boxShadow: `0 0 ${won ? 18 : 12}px ${tone}` }} />
        {lit && !reduce && <span key="ping" className="node-ping absolute inset-[-1px] rounded-full" style={{ borderColor: tone }} />}
      </motion.span>
      <motion.span aria-hidden className="absolute -left-[13px] top-[31px] h-px w-[13px] origin-left md:-left-[17px] md:w-[17px]"
        style={{ scaleX: p, background: `linear-gradient(90deg, ${tone}, transparent)` }} />
      <motion.div style={{ opacity: cardOpacity, x: cardX, y: cardY, filter: cardBlur }} className={won ? "beam" : ""}>
        <div className={won ? "beam-inner p-4 sm:p-5" : "surface p-4 sm:p-5"}>
          <div className="flex flex-wrap items-center gap-3">
            {a && <Avatar agent={a} size={36} />}
            <div className="min-w-[12rem] flex-1">
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
            <div className="mt-4 grid gap-1.5 sm:grid-cols-3 sm:gap-2">
              {e.candidates.map((c) => {
                const best = won && c.paired_delta != null && c.paired_delta === e.delta;
                return (
                  <div key={c.index} className={`rounded-xl border px-3 py-2.5 text-xs sm:p-3 ${best ? "border-line-strong bg-card-hover" : "border-line bg-card"}`}>
                    {/* phone: one compact row per rewrite; sm+: a small card */}
                    <div className="flex items-center gap-2 sm:hidden">
                      <span className="font-mono text-muted">#{c.index}</span>
                      <span className="min-w-0 flex-1 truncate font-medium text-ink2">{humanize(c.target)}</span>
                      {c.lint_ok ? <span className={`font-mono ${(c.paired_delta ?? 0) >= MARGIN ? "text-good" : "text-muted"}`}>{signedPct(c.paired_delta)}</span>
                        : <span className="font-mono text-bad">invalid</span>}
                      {best && <span className="text-[10px] uppercase tracking-wider text-good">win</span>}
                    </div>
                    <div className="hidden items-center justify-between sm:flex"><span className="font-mono text-muted">rewrite {c.index}</span>
                      {best && <span className="text-[10px] uppercase tracking-wider text-good">winner</span>}</div>
                    <div className="mt-1 hidden sm:block"><div className="line-clamp-1 font-medium text-ink2" title={c.target}>{humanize(c.target)}</div></div>
                    <div className="mt-2 hidden justify-between font-mono sm:flex">
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
              <button onClick={() => setOpen(!open)} className="-ml-1 inline-flex items-center gap-1 rounded-lg px-1 py-2 text-xs text-muted hover:text-ink">
                <ChevronDown size={13} className={`transition-transform ${open ? "rotate-180" : ""}`} /> Diagnosis that drove this generation
              </button>
              {open && <pre className="mt-1 max-h-80 overflow-auto overscroll-contain whitespace-pre-wrap break-words rounded-xl border border-line bg-bg2 p-3 font-mono text-[11px] leading-relaxed text-ink2">{e.diagnosis}</pre>}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

/** Where the best rewrite landed relative to the +3% gate, on a −10…+20 point scale. */
function Gate({ delta, won }: { delta: number | null; won: boolean }) {
  const lo = -0.1, hi = 0.2;
  const x = (v: number) => `${((Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)) * 100}%`;
  return (
    <div className="w-full sm:w-40" title="Best rewrite vs the promotion gate">
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
