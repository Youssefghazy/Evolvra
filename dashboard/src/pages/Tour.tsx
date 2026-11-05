import { useMemo, useRef, useState } from "react";
import { motion, useMotionValueEvent, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { useIsPhone } from "../lib/media";
import { ArrowRight, Dna, Gavel, Rocket, Trophy } from "lucide-react";
import { humanize, pct, providerName, type Data, type Mission } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { LogoMark } from "../components/Logo";
import MatrixTrail from "../components/MatrixTrail";
import { Rail, SectionHeader } from "../components/ui";

type Line = { text: string; tone?: "cmd" | "ok" | "warn" | "bad" | "dim" | "accent" };

const LID_CLOSED = -102; // degrees: lid folded flat onto the deck (180 - DECK_TILT, minus 2 so they never z-fight)
const DECK_TILT = 76;   // degrees: deck seen from slightly above, receding from the hinge

/** Turn a recorded mission into terminal lines: the replay is built from real data, not a mock. */
function replay(m: Mission): Line[] {
  const L: Line[] = [{ text: `❯ /evolvra:mission ${m.brief}`, tone: "cmd" },
    { text: `● mission started · ${m.mode} · ${m.tasks.length} tasks`, tone: "dim" }];
  const events: { at: string; line: Line }[] = [];
  const rejections = m.tasks.flatMap((t) => t.attempt_log.filter((a) => a.verdict === "FAIL" || a.verdict === "NEEDS_WORK")
    .filter((a) => !a.reopened_by_qa).map((a) => a.finished_at ?? a.started_at)).sort();
  for (const t of m.tasks) {
    for (const a of t.attempt_log) {
      const end = a.finished_at ?? a.started_at;
      events.push({ at: a.started_at, line: { text: `→ ${t.agent.padEnd(19)} attempt ${a.n} · ${t.task.slice(0, 54)}${t.task.length > 54 ? "…" : ""}`, tone: "accent" } });
      if (a.reopened_by_qa) {
        // the builder's attempt was handed back as done; QA's later rejection turned it into a FAIL
        events.push({ at: end, line: { text: "✓ handed to QA", tone: "dim" } });
        const qaAt = rejections.find((r) => r >= end) ?? end;
        events.push({ at: `${qaAt}~`, line: { text: `↻ QA rejected it · builder task ${t.no} reopened, the retry is charged to the builder`, tone: "warn" } });
        continue;
      }
      if (a.verdict) {
        const tone = a.verdict === "PASS" ? "ok" : a.verdict === "FAIL" ? "bad" : "warn";
        const note = (a.feedback ?? a.evidence ?? "").replace(/\s+/g, " ").slice(0, 70);
        events.push({ at: end, line: { text: `${a.verdict === "PASS" ? "✓" : "✗"} ${a.verdict.padEnd(10)} ${note}${note.length >= 70 ? "…" : ""}`, tone } });
      }
    }
  }
  events.sort((x, y) => x.at.localeCompare(y.at)).forEach((e) => L.push(e.line));
  L.push({ text: `● mission ${m.status} · scoring with three independent judges…`, tone: "dim" });
  for (const t of m.tasks) {
    const judges = [...new Set(t.scores.filter((s) => s.metric === "rubric:correctness" && !["ensemble", "deterministic"].includes(s.judge)).map((s) => s.judge))];
    const parts = judges.map((j) => `${providerName(j).model.slice(0, 14)} ${Math.round((t.scores.find((s) => s.judge === j && s.metric === "rubric:correctness")?.value ?? 0) * 100)}`);
    L.push({ text: `◆ ${t.agent.padEnd(19)} ${parts.join(" · ")}`, tone: "dim" });
    L.push({ text: `  fitness ${pct(t.fitness)}${t.attempts > 1 ? ` · ${t.attempts} attempts` : ""}`, tone: (t.fitness ?? 0) >= 0.9 ? "ok" : "warn" });
  }
  L.push({ text: "● exported · pushed · dashboard redeploying", tone: "ok" });
  return L;
}

export default function Tour({ data }: { data: Data }) {
  const mission = useMemo(() => data.missions.find((m) => m.tasks.some((t) => t.attempts > 1)) ?? data.missions[0], [data]);
  const lines = useMemo(() => (mission ? replay(mission) : []), [mission]);
  const phone = useIsPhone();
  return (
    <div className="space-y-12 md:space-y-24">
      <div className="relative pt-2 text-center md:pt-4">
        <div className="pointer-events-none absolute -top-20 bottom-[-6rem] left-1/2 -z-10 w-screen -translate-x-1/2 overflow-hidden">
          <div className="absolute inset-0"
            style={{ maskImage: "radial-gradient(ellipse 55% 65% at 50% 40%, #000 15%, transparent 72%)", WebkitMaskImage: "radial-gradient(ellipse 55% 65% at 50% 40%, #000 15%, transparent 72%)" }}>
            <MatrixTrail cell={20} ambient={0.0016} />
          </div>
        </div>
        <Reveal><div className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted">The tour</div></Reveal>
        <Reveal delay={0.05}><h1 className="mx-auto mt-3 max-w-3xl text-[2.1rem] font-semibold leading-[1.08] tracking-tight md:text-6xl">
          One mission, from brief to <span className="text-gradient">evolved agent</span></h1></Reveal>
        <Reveal delay={0.1}><p className="mx-auto mt-4 max-w-xl text-[15px] text-ink2 md:text-base">{phone ? "Scroll to play it back." : "Scroll to open the laptop."} The terminal replays a real recorded mission, including the moment QA sent the work back.</p></Reveal>
        <motion.div className="mx-auto mt-6 flex w-fit md:mt-8 flex-col items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-muted"
          animate={{ y: [0, 6, 0] }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}>
          scroll
          <span className="relative h-8 w-5 rounded-full border border-line-strong">
            <motion.span className="absolute left-1/2 top-1.5 h-1.5 w-1 -translate-x-1/2 rounded-full bg-ink2"
              animate={{ y: [0, 10, 0], opacity: [1, 0.2, 1] }} transition={{ duration: 1.8, repeat: Infinity }} />
          </span>
        </motion.div>
      </div>
      {phone ? <PhoneReplay lines={lines} title={mission?.brief ?? ""} /> : <MacbookScroll lines={lines} title={mission?.brief ?? ""} />}
      <Steps data={data} />
    </div>
  );
}

/* ------------------------------------------------------------------ macbook scroll */

function MacbookScroll({ lines, title }: { lines: Line[]; title: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  // Spring-smoothed: the lid glides between wheel ticks instead of stepping with them.
  const p = useSpring(scrollYProgress, { stiffness: 120, damping: 28, mass: 0.35, restDelta: 0.0005 });
  // One 3D scene: lid and deck share the same perspective, hinged on the same edge. The lid opens
  // fully first; the terminal only starts typing once it is upright, so it never types into a half-shut screen.
  const lid = useTransform(p, [0.02, 0.3], reduce ? [0, 0] : [LID_CLOSED, 0]);
  const lift = useTransform(p, [0.3, 0.92], reduce ? [1, 1] : [1, 1.1]);
  const rise = useTransform(p, [0.3, 0.92], reduce ? [0, 0] : [0, -30]);
  const glow = useTransform(p, [0.2, 0.36], [0, 1]);
  const shade = useTransform(p, [0.02, 0.3], [0.85, 0]);
  const [count, setCount] = useState(reduce ? lines.length : 0);
  useMotionValueEvent(p, "change", (v) => {
    if (reduce) return;
    setCount(Math.max(0, Math.min(lines.length, Math.round(((v - 0.34) / 0.56) * lines.length))));
  });

  return (
    <section ref={ref} className="relative h-[280vh]">
      <div className="sticky top-16 flex h-[calc(100vh-4rem)] items-center justify-center overflow-hidden"
        style={{ perspective: "1800px", perspectiveOrigin: "50% 30%" }}>
        <motion.div className="pointer-events-none absolute inset-x-0 top-1/3 mx-auto h-64 max-w-3xl rounded-full blur-3xl"
          style={{ opacity: glow, background: "radial-gradient(closest-side, var(--glow), transparent)" }} />
        <motion.div style={{ scale: lift, y: rise, transformStyle: "preserve-3d" }} className="relative w-[min(80vw,700px)]">
          {/* lid, hinged on its bottom edge; exactly as wide as the base, like a real laptop */}
          <motion.div style={{ rotateX: lid, transformOrigin: "50% 100%", transformStyle: "preserve-3d" }}
            className="relative mx-auto aspect-[16/10] w-full">
            {/* front: bezel + screen; hidden once the lid folds past vertical */}
            <div className="absolute inset-0 rounded-t-[18px] rounded-b-[3px] border border-neutral-700/70 bg-[#0b0b0f] p-[1.6%] shadow-2xl"
              style={{ backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}>
              <div className="absolute left-1/2 top-[0.7%] h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-neutral-700" />
              <div className="relative h-full overflow-hidden rounded-[8px] border border-neutral-800 bg-[#09090d]">
                <Terminal lines={lines} count={count} title={title} />
                {/* the screen stays dark until the lid is nearly upright */}
                <motion.div className="pointer-events-none absolute inset-0 bg-black" style={{ opacity: shade }} />
              </div>
            </div>
            {/* back: the aluminium shell you see while the lid is closed */}
            <div className="absolute inset-0 grid place-items-center rounded-t-[18px] rounded-b-[3px] border border-neutral-600/60 bg-gradient-to-b from-neutral-700 to-neutral-800"
              style={{ transform: "rotateX(180deg)", backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}>
              <LogoMark size={44} className="text-neutral-500/70" />
            </div>
          </motion.div>
          {/* hinge + deck: the deck tilts toward the viewer from the same hinge line, so it foreshortens like a real base */}
          <div className="relative mx-auto h-[10px] w-full rounded-t-[3px] bg-gradient-to-b from-neutral-600 to-neutral-800">
            <div className="absolute left-1/2 top-0 h-[5px] w-[16%] -translate-x-1/2 rounded-b-lg bg-neutral-900/80" />
          </div>
          <Keyboard />
        </motion.div>
      </div>
    </section>
  );
}

/**
 * Phone version of the replay. A laptop scaled to 390 px makes the terminal text unreadable, so on a
 * phone the terminal itself fills the screen: it pins under the header while you scroll, lines type
 * in at a readable 11 px and wrap instead of being cut, and a bar shows how far the replay has got.
 */
function PhoneReplay({ lines, title }: { lines: Line[]; title: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 60px", "end end"] });
  const bar = useTransform(scrollYProgress, [0.05, 0.9], [0, 1]);
  const [count, setCount] = useState(reduce ? lines.length : 1);
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    if (reduce) return;
    setCount(Math.max(1, Math.min(lines.length, Math.round(((v - 0.05) / 0.85) * lines.length))));
  });
  return (
    <section ref={ref} className="relative -mx-1" style={{ height: reduce ? "auto" : `${Math.max(220, lines.length * 14)}svh` }}>
      <div className={reduce ? "" : "sticky top-[64px] flex h-[calc(100svh-64px-56px-env(safe-area-inset-bottom))] items-center py-3"}>
        <div className="relative w-full">
          <div className="pointer-events-none absolute -inset-y-6 inset-x-0 -z-10 rounded-full blur-3xl" style={{ background: "radial-gradient(closest-side, var(--glow), transparent)" }} />
          <div className="overflow-hidden rounded-2xl border border-neutral-700/60 bg-[#09090d] shadow-2xl">
            <div className="h-0.5 bg-neutral-800"><motion.div className="h-full origin-left" style={{ scaleX: reduce ? 1 : bar, background: "linear-gradient(90deg, var(--accent), var(--accent-2))" }} /></div>
            <div className="h-[min(62svh,520px)]"><Terminal lines={lines} count={count} title={title} wrap /></div>
          </div>
          <div className="mt-3 flex items-center justify-between px-1 font-mono text-[11px] text-muted">
            <span>{count >= lines.length ? "replay complete" : "keep scrolling"}</span><span className="tnum">{count}/{lines.length}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function Terminal({ lines, count, title, wrap = false }: { lines: Line[]; count: number; title: string; wrap?: boolean }) {
  const tone: Record<string, string> = {
    cmd: "text-white", ok: "text-emerald-400", warn: "text-amber-300", bad: "text-rose-400", dim: "text-neutral-500", accent: "text-cyan-300",
  };
  const shown = lines.slice(0, count);
  return (
    <div className={`flex h-full flex-col font-mono leading-[1.55] ${wrap ? "text-[11px]" : "text-[clamp(7px,1.15vw,11.5px)]"}`}>
      <div className="flex items-center gap-1.5 border-b border-neutral-800 px-3 py-1.5">
        <span className="h-2 w-2 rounded-full bg-rose-500/80" /><span className="h-2 w-2 rounded-full bg-amber-400/80" /><span className="h-2 w-2 rounded-full bg-emerald-500/80" />
        <span className="ml-2 flex min-w-0 items-center gap-1.5 text-[0.9em] text-neutral-500"><LogoMark size={11} /><span className="truncate">claude · ~/Evolvra · {title.slice(0, 48)}</span></span>
      </div>
      <div className={`flex flex-1 flex-col justify-end overflow-hidden px-3 py-2 ${wrap ? "[mask-image:linear-gradient(transparent,#000_16%)]" : ""}`}>
        {shown.slice(wrap ? -14 : -17).map((l, i) => (
          <motion.div key={`${i}-${l.text}`} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.18 }}
            className={`${wrap ? "mb-1 whitespace-pre-wrap break-words [overflow-wrap:anywhere]" : "whitespace-pre truncate"} ${tone[l.tone ?? "dim"]}`}>{wrap ? l.text.replace(/ {2,}/g, " ") : l.text}</motion.div>
        ))}
        <div className="text-neutral-400">{count >= lines.length ? "❯ " : ""}<span className="inline-block h-[1em] w-[0.55em] translate-y-[2px] animate-pulse bg-neutral-400" /></div>
      </div>
    </div>
  );
}

function Keyboard() {
  const rows = [14, 14, 13, 12, 10];
  return (
    <div className="mx-auto w-full rounded-b-[20px] border-x border-b border-neutral-700/60 bg-gradient-to-b from-neutral-800 to-neutral-900 px-[4%] pb-[2.5%] pt-[2.2%] shadow-[0_40px_60px_-20px_rgba(0,0,0,0.85)]"
      style={{ transform: `rotateX(${DECK_TILT}deg)`, transformOrigin: "50% 0%" }}>
      <div className="space-y-[0.6%]">
        {rows.map((n, r) => (
          <div key={r} className="flex gap-[0.6%]">
            {Array.from({ length: n }).map((_, k) => (
              <span key={k} className="h-4 flex-1 rounded-[3px] bg-neutral-950/80 shadow-[inset_0_-1px_0_rgba(255,255,255,0.04)]"
                style={{ flexGrow: r === 4 && k === 4 ? 5 : 1 }} />
            ))}
          </div>
        ))}
      </div>
      <div className="mx-auto mt-[3%] h-16 w-[38%] rounded-lg border border-neutral-700/50 bg-neutral-800/60" />
    </div>
  );
}

/* ------------------------------------------------------------------ steps */

function Steps({ data }: { data: Data }) {
  const promo = [...data.evolutions].reverse().find((e) => e.winner_version != null);
  const steps = [
    { icon: Rocket, title: "A brief goes in", to: href.missions, text: "You type one sentence. The orchestrator picks specialists, writes each a task with measurable acceptance criteria, and records every step." },
    { icon: Gavel, title: "Independent judges grade it", to: href.control, text: "Three free models from three labs score correctness, completeness, quality and evidence. Word and byte counts are measured by code." },
    { icon: Dna, title: "The weakest agent is diagnosed", to: href.evolutions, text: "Its worst real tasks become a diagnosis. A coach model writes three rewrites of its persona, each fixing one named failure." },
    { icon: Trophy, title: "Only a winner ships", to: promo ? href.agent(promo.agent) : href.evolutions, text: promo ? `Rewrites play the original on held-out tasks. ${humanize(promo.agent)} v${promo.winner_version} won by ${Math.round((promo.delta ?? 0) * 1000) / 10} points and is live now.` : "Rewrites play the original on held-out tasks; a new version ships only if it clearly wins." },
  ];
  return (
    <section>
      <Reveal><SectionHeader eyebrow="What just happened" title="Four steps, every one on the record" /></Reveal>
      <Rail cols="md:grid-cols-2">{steps.map((s, i) => (
          <Reveal key={s.title} delay={i * 0.06} className="h-full">
            <Spotlight href={s.to} className="block h-full p-5 md:p-6">
              <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-line-strong bg-card-solid"><s.icon size={18} className="text-accent" /></span>
                <span className="font-mono text-xs text-muted">step {i + 1}</span></div>
              <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink2">{s.text}</p>
            </Spotlight>
          </Reveal>
        ))}</Rail>
      <div className="mt-8 flex justify-center md:mt-10">
        <a href={href.control} style={{ background: "var(--ink)", color: "var(--bg)" }} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full px-5 text-[15px] font-medium transition-transform active:scale-[0.98] sm:h-auto sm:w-auto sm:py-2.5 sm:text-sm">
          Open the control room <ArrowRight size={15} />
        </a>
      </div>
    </section>
  );
}
