import { useMemo, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight, ArrowUpRight, Dna, Gavel, Rocket, Sparkles, Trophy } from "lucide-react";
import {
  addedLines, grade, humanize, latestPromotion, pct, relTime, signedPct, toneVar, type Agent, type Data,
} from "../data";
import { href } from "../lib/router";
import { NumberTicker, Reveal, Spotlight, WordsReveal } from "../components/fx";
import { Avatar, Bar, Chip, GithubIcon, SectionHeader, Verdict } from "../components/ui";

export default function Home({ data }: { data: Data }) {
  const s = data.summary;
  const calls = s.providers.reduce((n, p) => n + (p.requests || 0), 0);
  const refused = data.evolutions.filter((e) => e.winner_version == null).length;
  const promo = latestPromotion(data);
  return (
    <div className="space-y-20 md:space-y-28">
      <Hero data={data} promotedSlug={promo?.agent.slug} />

      <Reveal>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <MiniStat label="Missions" value={s.missions} />
          <MiniStat label="Tasks graded" value={s.tasks} />
          <MiniStat label="Generations" value={s.evolutions} />
          <MiniStat label="Promotions" value={s.promotions} />
          <MiniStat label="Free-tier calls" value={calls} />
          <div className="beam"><div className="beam-inner h-full p-4">
            <div className="text-xs text-muted">Money spent</div>
            <div className="mt-1.5 font-mono text-2xl font-semibold tracking-tight text-gradient">$0.00</div>
            <div className="mt-0.5 text-[11px] text-muted">by design</div>
          </div></div>
        </div>
      </Reveal>

      <Pipeline data={data} calls={calls} refused={refused} />

      {promo && <Promotion data={data} />}

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="min-w-0 lg:col-span-3"><RosterHealth agents={data.agents} /></div>
        <div className="min-w-0 lg:col-span-2"><EvolutionLog data={data} /></div>
      </div>

      <RecentMissions data={data} />
    </div>
  );
}

/* ---------------------------------------------------------------- hero */

function Hero({ data, promotedSlug }: { data: Data; promotedSlug?: string }) {
  return (
    <section className="grid items-center gap-10 pt-6 md:pt-14 lg:grid-cols-[1.1fr_1fr]">
      <div>
        <motion.a href={href.evolutions} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1 text-xs text-ink2 hover:border-line-strong">
          <Sparkles size={12} className="text-accent" />
          {data.summary.promotions} promotion{data.summary.promotions === 1 ? "" : "s"} earned · last cycle {relTime(data.summary.generated_at)}
          <ArrowRight size={12} />
        </motion.a>
        <h1 className="mt-6 text-4xl font-semibold leading-[1.05] tracking-tight md:text-6xl">
          <WordsReveal text="AI agents that evolve themselves." />
          <br />
          <WordsReveal text="With receipts." delay={0.35} className="text-gradient" />
        </h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-6 max-w-xl text-base leading-relaxed text-ink2 md:text-lg">
          Evolvra runs a team of AI specialists on real missions, has three independent judges grade every result,
          and rewrites the weakest agent's playbook. A new version ships only when it beats the old one.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.5 }}
          className="mt-8 flex flex-wrap items-center gap-3">
          <a href={href.agents} style={{ background: "var(--ink)", color: "var(--bg)" }} className="group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-transform hover:-translate-y-0.5">
            Meet the agents <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
          </a>
          <a href="https://github.com/Youssefghazy/Evolvra" target="_blank" rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-5 py-2.5 text-sm text-ink2 hover:text-ink">
            <GithubIcon size={15} /> Source on GitHub
          </a>
        </motion.div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }} className="mt-8 flex flex-wrap gap-2">
          <Chip tone="var(--good)">$0 budget, free tiers only</Chip>
          <Chip tone="var(--accent)">Runs every 6 hours, unattended</Chip>
          <Chip tone="var(--accent-2)">3 judges from 3 labs</Chip>
        </motion.div>
      </div>
      <AgentOrbit agents={data.agents} promotedSlug={promotedSlug} promotions={data.summary.promotions} />
    </section>
  );
}

function AgentOrbit({ agents, promotedSlug, promotions }: { agents: Agent[]; promotedSlug?: string; promotions: number }) {
  const [hover, setHover] = useState<Agent | null>(null);
  const inner = agents.slice(0, 4), outer = agents.slice(4);
  const place = (list: Agent[], radius: number, offset: number) =>
    list.map((a, i) => {
      const t = (i / list.length) * Math.PI * 2 + offset;
      return { a, x: Math.cos(t) * radius, y: Math.sin(t) * radius };
    });
  const nodes = [...place(inner, 27, 0.4), ...place(outer, 45, 0)];
  return (
    <motion.div initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
      className={`relative mx-auto aspect-square w-full max-w-[460px] ${hover ? "orbit-paused" : ""}`}>
      <div className="absolute inset-[5%] rounded-full border border-dashed border-line" />
      <div className="absolute inset-[23%] rounded-full border border-line" />
      <div className="absolute inset-[38%] rounded-full" style={{ background: "radial-gradient(circle, var(--glow), transparent 70%)" }} />
      <div className="absolute inset-0 grid place-items-center">
        <div className="grid h-24 w-24 place-items-center rounded-full border border-line-strong bg-card-solid text-center shadow-2xl"
          style={{ boxShadow: "0 0 60px -10px var(--accent-2)" }}>
          <div>
            <div className="text-2xl">🧬</div>
            <div className="mt-0.5 font-mono text-[10px] uppercase tracking-widest text-muted">{promotions} evolved</div>
          </div>
        </div>
      </div>
      <div className="orbit absolute inset-0">
        {nodes.map(({ a, x, y }) => {
          const promoted = a.slug === promotedSlug;
          return (
            <a key={a.slug} href={href.agent(a.slug)} onMouseEnter={() => setHover(a)} onMouseLeave={() => setHover(null)}
              className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: `${50 + x}%`, top: `${50 + y}%` }}
              aria-label={a.name}>
              <span className="orbit-counter block transition-transform duration-300 hover:scale-110">
                <span className="relative block">
                  {promoted && <span className="absolute -inset-2 rounded-full" style={{ boxShadow: "0 0 26px 2px var(--good)" }} />}
                  <Avatar agent={a} size={promoted ? 54 : 44} />
                  {promoted && (
                    <span className="absolute -right-2 -top-1 rounded-full border border-line bg-card-solid px-1.5 font-mono text-[10px] text-good">
                      v{a.current_version}
                    </span>
                  )}
                </span>
              </span>
            </a>
          );
        })}
      </div>
      <div className="pointer-events-none absolute inset-x-0 -bottom-2 flex justify-center">
        <div className={`rounded-full border border-line bg-card-solid px-3 py-1 text-xs transition-opacity ${hover ? "opacity-100" : "opacity-0"}`}>
          {hover && (<><span className="font-medium">{hover.name}</span> <span className="text-muted">· fitness {pct(hover.fitness)} · v{hover.current_version}</span></>)}
        </div>
      </div>
    </motion.div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="surface p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1.5 text-2xl font-semibold tracking-tight"><NumberTicker value={value} /></div>
    </div>
  );
}

/* ---------------------------------------------------------------- pipeline */

function Pipeline({ data, calls, refused }: { data: Data; calls: number; refused: number }) {
  const steps = [
    { icon: Rocket, title: "Mission", text: "Claude Code runs a brief through specialist agents. Every handoff, attempt and verdict is recorded.",
      metric: `${data.summary.missions} missions` },
    { icon: Gavel, title: "Judge", text: "Three free models from three labs grade each deliverable. Counts are measured by code, never guessed.",
      metric: `${data.summary.tasks} tasks · ${calls} calls` },
    { icon: Dna, title: "Evolve", text: "The weakest agent's failures become a diagnosis. An AI coach writes three targeted rewrites of its playbook.",
      metric: `${data.summary.evolutions} generations` },
    { icon: Trophy, title: "Promote", text: "Each rewrite fights the original on held-out tasks. A new version ships only if it clearly wins.",
      metric: `${data.summary.promotions} promoted · ${refused} refused` },
  ];
  return (
    <section>
      <Reveal><SectionHeader eyebrow="How it works" title="A closed loop, with a gate at the end"
        sub="Most AI teams hand-tune their prompts and hope. Evolvra measures, rewrites and tests them, and keeps only what wins." /></Reveal>
      <div className="relative grid gap-4 md:grid-cols-4">
        <svg className="pointer-events-none absolute left-0 top-[52px] hidden h-2 w-full md:block" preserveAspectRatio="none" viewBox="0 0 100 2">
          <defs>
            <linearGradient id="flowg" x1="0" x2="1">
              <stop offset="0" stopColor="var(--accent)" /><stop offset="0.5" stopColor="var(--accent-2)" /><stop offset="1" stopColor="var(--accent-3)" />
            </linearGradient>
          </defs>
          <line x1="12" y1="1" x2="88" y2="1" stroke="var(--line)" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />
          <line x1="12" y1="1" x2="88" y2="1" stroke="url(#flowg)" strokeWidth="2" className="flow" vectorEffect="non-scaling-stroke" />
        </svg>
        {steps.map((st, i) => (
          <Reveal key={st.title} delay={i * 0.1}>
            <Spotlight className="h-full p-5">
              <div className="flex items-center justify-between">
                <span className="relative z-10 grid h-11 w-11 place-items-center rounded-xl border border-line-strong bg-card-solid">
                  <st.icon size={18} className="text-accent" />
                </span>
                <span className="font-mono text-xs text-muted">0{i + 1}</span>
              </div>
              <h3 className="mt-5 text-base font-semibold">{st.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink2">{st.text}</p>
              <div className="mt-4 font-mono text-xs text-accent">{st.metric}</div>
            </Spotlight>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- promotion */

function Promotion({ data }: { data: Data }) {
  const p = latestPromotion(data)!;
  const { agent, parent, winner, cand, promo } = p;
  const lines = useMemo(() => (parent && winner ? addedLines(parent.content, winner.content, 4) : []), [parent, winner]);
  const realUp = parent?.fitness != null && winner?.fitness != null && winner.fitness >= parent.fitness;
  return (
    <section>
      <Reveal><SectionHeader eyebrow="Latest promotion" title={<>An agent rewrote its own playbook, and it worked</>}
        action={<a href={href.agent(agent.slug)} className="hidden items-center gap-1 text-sm text-accent hover:underline sm:inline-flex">Full diff <ArrowUpRight size={14} /></a>} /></Reveal>
      <Reveal delay={0.05}>
        <div className="beam"><div className="beam-inner grid gap-8 p-6 md:p-8 lg:grid-cols-[1fr_1.1fr_1fr]">
          <div>
            <div className="flex items-center gap-4">
              <Avatar agent={agent} size={64} />
              <div>
                <div className="text-xl font-semibold">{agent.name}</div>
                <div className="mt-1 flex items-center gap-2 font-mono text-sm">
                  <span className="rounded-md border border-line px-1.5 text-muted">v{promo.parent_version}</span>
                  <ArrowRight size={14} className="text-muted" />
                  <span className="rounded-md border px-1.5 text-good" style={{ borderColor: "var(--good)" }}>v{promo.winner_version}</span>
                </div>
              </div>
            </div>
            <p className="mt-5 text-sm leading-relaxed text-ink2">
              The judges kept flagging <span className="text-ink">{humanize(cand?.target ?? "weak spots")}</span>. Evolution wrote
              three rewrites; this one beat the original on every held-out task it played, then held up on real work.
            </p>
            <div className="mt-4"><Chip tone={realUp ? "var(--good)" : "var(--warn)"}>{realUp ? "Holding up on real missions" : "Awaiting more real missions"}</Chip></div>
          </div>
          <div className="space-y-6">
            <Dumbbell label="Arena · held-out tasks" a={promo.parent_fitness ?? null} b={cand?.fitness ?? null}
              note={`${cand?.shared_tasks ?? "–"} shared tasks · paired ${signedPct(promo.delta)}`} />
            <Dumbbell label="Real missions" a={parent?.fitness ?? null} b={winner?.fitness ?? null}
              note={`${parent?.tasks ?? 0} tasks on v${promo.parent_version} · ${winner?.tasks ?? 0} on v${promo.winner_version}`} />
          </div>
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.16em] text-muted">What it learned</div>
            <ul className="mt-3 space-y-2.5">
              {lines.map((l, i) => (
                <li key={i} className="flex gap-2 text-sm leading-snug text-ink2">
                  <span className="mt-0.5 font-mono text-good">+</span><span className="line-clamp-2">{l}</span>
                </li>
              ))}
            </ul>
            <a href={href.agent(agent.slug)} className="mt-4 inline-flex items-center gap-1 text-sm text-accent hover:underline">See the exact diff <ArrowRight size={14} /></a>
          </div>
        </div></div>
      </Reveal>
    </section>
  );
}

/** Before → after on one 0–100 scale: two dots joined by a line. */
function Dumbbell({ label, a, b, note }: { label: string; a: number | null; b: number | null; note: string }) {
  const MIN = 0.5; // every score here sits above 50; the axis is labelled so the zoom is explicit
  const sx = (v: number) => (Math.max(MIN, Math.min(1, v)) - MIN) / (1 - MIN);
  const lo = sx(Math.min(a ?? MIN, b ?? MIN)), hi = sx(Math.max(a ?? MIN, b ?? MIN));
  const up = a != null && b != null && b >= a;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.16em] text-muted">{label}</span>
        <span className="font-mono text-sm"><span className="text-muted">{pct(a)}</span> <span className="text-muted">→</span>{" "}
          <span className="text-lg font-semibold" style={{ color: up ? "var(--good)" : "var(--bad)" }}>{pct(b)}</span></span>
      </div>
      <div className="relative mt-3 h-6">
        <div className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-line" />
        {[0, 0.5, 1].map((t) => <div key={t} className="absolute top-1/2 h-2 w-px -translate-y-1/2 bg-line" style={{ left: `${t * 100}%` }} />)}
        <motion.div className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded-full"
          style={{ left: `${lo * 100}%`, background: up ? "var(--good)" : "var(--bad)" }}
          initial={{ width: 0 }} whileInView={{ width: `${(hi - lo) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.9, delay: 0.2 }} />
        {a != null && <span className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-muted bg-card-solid" style={{ left: `${sx(a) * 100}%` }} />}
        {b != null && <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ left: `${sx(b) * 100}%`, background: up ? "var(--good)" : "var(--bad)", boxShadow: "0 0 0 3px var(--card-solid)" }} />}
      </div>
      <div className="flex justify-between font-mono text-[10px] text-muted"><span>50</span><span>75</span><span>100</span></div>
      <div className="mt-1 text-[11px] text-muted">{note}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- roster health */

function RosterHealth({ agents }: { agents: Agent[] }) {
  const scored = agents.filter((a) => a.fitness != null).sort((x, y) => (y.fitness ?? 0) - (x.fitness ?? 0));
  const weakest = scored[scored.length - 1]?.slug;
  return (
    <Reveal className="h-full">
      <div className="surface h-full p-5 md:p-6">
        <SectionHeader eyebrow="Roster health" title="Fitness by agent"
          sub="Current version, graded by at least two judges. The weakest agent is the next to evolve." />
        <ul className="space-y-3">
          {scored.map((a) => {
            const isWeak = a.slug === weakest;
            const cur = a.versions.find((v) => v.version === a.current_version);
            return (
              <li key={a.slug}>
                <a href={href.agent(a.slug)} className="group grid grid-cols-[1.75rem_9.5rem_1fr_3rem] items-center gap-3 rounded-lg py-0.5"
                  title={`${a.tasks} tasks · v${a.current_version}${cur?.top_failure ? ` · top issue: ${humanize(cur.top_failure)}` : ""}`}>
                  <Avatar agent={a} size={26} />
                  <span className="truncate text-sm text-ink2 group-hover:text-ink">{a.name}</span>
                  <div className="relative">
                    <Bar value={a.fitness} height={8} color={isWeak ? "var(--warn)" : "color-mix(in srgb, var(--ink-2) 55%, transparent)"} />
                    {isWeak && <span className="absolute -top-5 right-0 text-[10px] font-medium uppercase tracking-wider text-warn">next to evolve</span>}
                  </div>
                  <span className="text-right font-mono text-sm tnum">{Math.round((a.fitness ?? 0) * 100)}</span>
                </a>
              </li>
            );
          })}
        </ul>
      </div>
    </Reveal>
  );
}

/* ---------------------------------------------------------------- evolution log */

function EvolutionLog({ data }: { data: Data }) {
  const list = [...data.evolutions].reverse().slice(0, 6);
  return (
    <Reveal className="h-full" delay={0.08}>
      <div className="surface h-full p-5 md:p-6">
        <SectionHeader eyebrow="Evolution log" title="Recent generations"
          action={<a href={href.evolutions} className="text-sm text-accent hover:underline">All</a>} />
        <ol className="relative space-y-4 border-l border-line pl-5">
          {list.map((e) => {
            const a = data.agents.find((x) => x.slug === e.agent);
            const won = e.winner_version != null;
            return (
              <li key={e.id} className="relative">
                <span className="absolute -left-[26px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-bg"
                  style={{ background: won ? "var(--good)" : "var(--line-strong)", boxShadow: won ? "0 0 12px var(--good)" : undefined }} />
                <div className="flex items-center gap-2 text-sm">
                  {a && <Avatar agent={a} size={20} />}
                  <span className="font-medium">{a?.name ?? e.agent}</span>
                  <span className={`ml-auto font-mono text-xs ${won ? "text-good" : "text-muted"}`}>{won ? `→ v${e.winner_version}` : "refused"}</span>
                </div>
                <div className="mt-0.5 text-xs text-muted">
                  {won ? `Won by ${signedPct(e.delta)}` : e.delta == null ? "No fair comparison possible" : `Best rewrite ${signedPct(e.delta)}, needed +3.0%`} · {relTime(e.created_at)}
                </div>
              </li>
            );
          })}
        </ol>
      </div>
    </Reveal>
  );
}

/* ---------------------------------------------------------------- missions */

function RecentMissions({ data }: { data: Data }) {
  const list = data.missions.slice(0, 4);
  return (
    <section>
      <Reveal><SectionHeader eyebrow="Recent missions" title="What the agency worked on"
        action={<a href={href.missions} className="text-sm text-accent hover:underline">All missions</a>} /></Reveal>
      <div className="grid gap-4 md:grid-cols-2">
        {list.map((m, i) => {
          const fits = m.tasks.map((t) => t.fitness).filter((f): f is number => f != null);
          const avg = fits.length ? fits.reduce((x, y) => x + y, 0) / fits.length : null;
          const g = grade(avg);
          const retries = m.tasks.reduce((n, t) => n + Math.max(0, t.attempts - 1), 0);
          return (
            <Reveal key={m.id} delay={i * 0.06}>
              <Spotlight as="a" href={href.mission(m.id)} className="block h-full p-5">
                <div className="flex items-center justify-between gap-3">
                  <Verdict v={m.status} />
                  <span className="text-xs text-muted">{relTime(m.started_at)}</span>
                </div>
                <p className="mt-3 line-clamp-2 font-medium leading-snug">{m.brief}</p>
                <div className="mt-4 flex items-center justify-between">
                  <div className="flex -space-x-2">
                    {m.tasks.map((t) => {
                      const a = data.agents.find((x) => x.slug === t.agent);
                      return a ? <Avatar key={t.no} agent={a} size={28} /> : null;
                    })}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted">
                    {retries > 0 && <span className="text-warn">{retries} retr{retries === 1 ? "y" : "ies"}</span>}
                    <span>{m.tasks.length} tasks</span>
                    <span className="font-mono text-sm" style={{ color: toneVar[g.tone] }}>{pct(avg)}</span>
                  </div>
                </div>
              </Spotlight>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}
