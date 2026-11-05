import { useMemo, useRef } from "react";
import { motion, useMotionValueEvent, useReducedMotion, useScroll, useTransform } from "motion/react";
import { useState } from "react";
import { ArrowRight, Dna, Gavel, Rocket, Trophy } from "lucide-react";
import { humanize, pct, providerName, type Data, type Mission } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { LogoMark } from "../components/Logo";
import MatrixTrail from "../components/MatrixTrail";
import { SectionHeader } from "../components/ui";

type Line = { text: string; tone?: "cmd" | "ok" | "warn" | "bad" | "dim" | "accent" };

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
  return (
    <div className="space-y-24">
      <div className="relative pt-4 text-center">
        <div className="pointer-events-none absolute -inset-x-[50vw] -top-20 bottom-[-6rem] -z-10"
          style={{ maskImage: "radial-gradient(ellipse 55% 65% at 50% 40%, #000 15%, transparent 72%)", WebkitMaskImage: "radial-gradient(ellipse 55% 65% at 50% 40%, #000 15%, transparent 72%)" }}>
          <MatrixTrail cell={20} ambient={0.0016} />
        </div>
        <Reveal><div className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted">The tour</div></Reveal>
        <Reveal delay={0.05}><h1 className="mx-auto mt-3 max-w-3xl text-4xl font-semibold tracking-tight md:text-6xl">
          One mission, from brief to <span className="text-gradient">evolved agent</span></h1></Reveal>
        <Reveal delay={0.1}><p className="mx-auto mt-4 max-w-xl text-ink2">Scroll to open the laptop. The terminal replays a real recorded mission, including the moment QA sent the work back.</p></Reveal>
        <motion.div className="mx-auto mt-8 flex w-fit flex-col items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-muted"
          animate={{ y: [0, 6, 0] }} transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}>
          scroll
          <span className="relative h-8 w-5 rounded-full border border-line-strong">
            <motion.span className="absolute left-1/2 top-1.5 h-1.5 w-1 -translate-x-1/2 rounded-full bg-ink2"
              animate={{ y: [0, 10, 0], opacity: [1, 0.2, 1] }} transition={{ duration: 1.8, repeat: Infinity }} />
          </span>
        </motion.div>
      </div>
      <MacbookScroll lines={lines} title={mission?.brief ?? ""} />
      <Steps data={data} />
    </div>
  );
}

/* ------------------------------------------------------------------ macbook scroll */

function MacbookScroll({ lines, title }: { lines: Line[]; title: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const lid = useTransform(scrollYProgress, [0, 0.28], reduce ? [0, 0] : [-68, 0]);
  const lift = useTransform(scrollYProgress, [0.28, 0.9], reduce ? [1, 1] : [1, 1.18]);
  const rise = useTransform(scrollYProgress, [0.28, 0.9], reduce ? [0, 0] : [0, -40]);
  const glow = useTransform(scrollYProgress, [0.15, 0.35], [0, 1]);
  const [count, setCount] = useState(reduce ? lines.length : 0);
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    if (reduce) return;
    setCount(Math.max(0, Math.min(lines.length, Math.round(((v - 0.22) / 0.62) * lines.length))));
  });

  return (
    <section ref={ref} className="relative h-[260vh]">
      <div className="sticky top-16 flex h-[calc(100vh-4rem)] items-center justify-center overflow-hidden [perspective:1600px]">
        <motion.div className="pointer-events-none absolute inset-x-0 top-1/3 mx-auto h-64 max-w-3xl rounded-full blur-3xl"
          style={{ opacity: glow, background: "radial-gradient(closest-side, var(--glow), transparent)" }} />
        <motion.div style={{ scale: lift, y: rise }} className="relative w-[min(92vw,820px)]">
          {/* lid */}
          <motion.div style={{ rotateX: lid, transformOrigin: "bottom center", transformStyle: "preserve-3d" }}
            className="relative mx-auto aspect-[16/10] w-[88%] rounded-t-[18px] rounded-b-[4px] border border-neutral-700/60 bg-[#0b0b0f] p-[1.6%] shadow-2xl">
            <div className="absolute left-1/2 top-[0.7%] h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-neutral-700" />
            <div className="relative h-full overflow-hidden rounded-[8px] border border-neutral-800 bg-[#09090d]">
              <Terminal lines={lines} count={count} title={title} />
            </div>
          </motion.div>
          {/* base */}
          <div className="relative mx-auto -mt-px h-[18px] w-full rounded-b-[18px] rounded-t-[3px] border border-neutral-700/60 bg-gradient-to-b from-neutral-700 to-neutral-900 shadow-[0_30px_60px_-20px_rgba(0,0,0,0.8)]">
            <div className="absolute left-1/2 top-0 h-[6px] w-[16%] -translate-x-1/2 rounded-b-xl bg-neutral-800" />
          </div>
          <Keyboard />
        </motion.div>
      </div>
    </section>
  );
}

function Terminal({ lines, count, title }: { lines: Line[]; count: number; title: string }) {
  const tone: Record<string, string> = {
    cmd: "text-white", ok: "text-emerald-400", warn: "text-amber-300", bad: "text-rose-400", dim: "text-neutral-500", accent: "text-cyan-300",
  };
  const shown = lines.slice(0, count);
  return (
    <div className="flex h-full flex-col font-mono text-[clamp(7px,1.15vw,11.5px)] leading-[1.55]">
      <div className="flex items-center gap-1.5 border-b border-neutral-800 px-3 py-1.5">
        <span className="h-2 w-2 rounded-full bg-rose-500/80" /><span className="h-2 w-2 rounded-full bg-amber-400/80" /><span className="h-2 w-2 rounded-full bg-emerald-500/80" />
        <span className="ml-2 flex items-center gap-1.5 truncate text-[0.9em] text-neutral-500"><LogoMark size={11} /> claude · ~/Evolvra · {title.slice(0, 48)}</span>
      </div>
      <div className="flex flex-1 flex-col justify-end overflow-hidden px-3 py-2">
        {shown.slice(-17).map((l, i) => (
          <motion.div key={`${i}-${l.text}`} initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.18 }}
            className={`whitespace-pre truncate ${tone[l.tone ?? "dim"]}`}>{l.text}</motion.div>
        ))}
        <div className="text-neutral-400">{count >= lines.length ? "❯ " : ""}<span className="inline-block h-[1em] w-[0.55em] translate-y-[2px] animate-pulse bg-neutral-400" /></div>
      </div>
    </div>
  );
}

function Keyboard() {
  const rows = [14, 14, 13, 12, 10];
  return (
    <div className="mx-auto mt-[-1px] hidden w-[94%] rounded-b-[22px] border-x border-b border-neutral-800 bg-gradient-to-b from-neutral-900 to-[#0c0c10] px-[4%] pb-[3%] pt-[2.4%] sm:block"
      style={{ transform: "perspective(900px) rotateX(58deg)", transformOrigin: "top center" }}>
      <div className="space-y-[0.6%]">
        {rows.map((n, r) => (
          <div key={r} className="flex gap-[0.6%]">
            {Array.from({ length: n }).map((_, k) => (
              <span key={k} className="h-3 flex-1 rounded-[3px] bg-neutral-800/90 shadow-[inset_0_-1px_0_rgba(0,0,0,0.6)]"
                style={{ flexGrow: r === 4 && k === 4 ? 5 : 1 }} />
            ))}
          </div>
        ))}
      </div>
      <div className="mx-auto mt-[3%] h-10 w-[38%] rounded-lg border border-neutral-800 bg-neutral-900/80" />
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
      <div className="grid gap-4 md:grid-cols-2">
        {steps.map((s, i) => (
          <Reveal key={s.title} delay={i * 0.06}>
            <Spotlight href={s.to} className="block h-full p-6">
              <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-line-strong bg-card-solid"><s.icon size={18} className="text-accent" /></span>
                <span className="font-mono text-xs text-muted">step {i + 1}</span></div>
              <h3 className="mt-4 text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink2">{s.text}</p>
            </Spotlight>
          </Reveal>
        ))}
      </div>
      <div className="mt-10 flex justify-center">
        <a href={href.control} style={{ background: "var(--ink)", color: "var(--bg)" }} className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium">
          Open the control room <ArrowRight size={15} />
        </a>
      </div>
    </section>
  );
}
