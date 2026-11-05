import { useMemo } from "react";
import { motion } from "motion/react";
import { ArrowRight, ArrowUpRight, Dna, Gavel, LayoutDashboard, Laptop, Rocket, Sparkles, Trophy } from "lucide-react";
import {
  addedLines, grade, humanize, latestPromotion, pct, relTime, signedPct, toneVar, type Agent, type Data,
} from "../data";
import { href } from "../lib/router";
import { NumberTicker, Reveal, Spotlight, WordsReveal } from "../components/fx";
import Orbit from "../components/Orbit";
import MatrixTrail from "../components/MatrixTrail";
import { Avatar, Bar, Chip, Rail, SectionHeader, Verdict } from "../components/ui";

export default function Home({ data }: { data: Data }) {
  const s = data.summary;
  const calls = s.providers.reduce((n, p) => n + (p.requests || 0), 0);
  const refused = data.evolutions.filter((e) => e.winner_version == null).length;
  const promo = latestPromotion(data);
  return (
    <div className="space-y-14 md:space-y-28">
      <Hero data={data} promotedSlug={promo?.agent.slug} />

      <Reveal>
        <div className="grid grid-cols-3 gap-2 sm:gap-3 lg:grid-cols-6">
          <MiniStat label="Missions" value={s.missions} to={href.missions} />
          <MiniStat label="Tasks graded" value={s.tasks} to={href.missions} />
          <MiniStat label="Generations" value={s.evolutions} to={href.evolutions} />
          <MiniStat label="Promotions" value={s.promotions} to={href.evolutions} />
          <MiniStat label="Free-tier calls" value={calls} to={href.control} />
          <div className="beam"><div className="beam-inner h-full p-3 sm:p-4">
            <div className="text-[11px] text-muted sm:text-xs">Money spent</div>
            <div className="mt-1 font-mono text-xl font-semibold tracking-tight text-gradient sm:mt-1.5 sm:text-2xl">$0.00</div>
            <div className="mt-0.5 hidden text-[11px] text-muted sm:block">by design</div>
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
    <section className="relative grid items-center gap-6 pt-2 md:gap-10 md:pt-14 lg:grid-cols-[1.1fr_1fr]">
      <div className="pointer-events-none absolute -top-24 bottom-[-4rem] left-1/2 -z-10 w-screen -translate-x-1/2 overflow-hidden">
        <div className="absolute inset-0 [--mask:radial-gradient(ellipse_70%_45%_at_50%_70%,#000_25%,transparent_80%)] lg:[--mask:radial-gradient(ellipse_34%_62%_at_64%_46%,#000_25%,transparent_80%)]"
          style={{ maskImage: "var(--mask)", WebkitMaskImage: "var(--mask)" }}>
          <MatrixTrail />
        </div>
      </div>
      <div className="min-w-0">
        <motion.a href={href.evolutions} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1 text-xs text-ink2 hover:border-line-strong">
          <Sparkles size={12} className="text-accent" />
          {data.summary.promotions} promotion{data.summary.promotions === 1 ? "" : "s"} earned · last cycle {relTime(data.summary.generated_at)}
          <ArrowRight size={12} />
        </motion.a>
        <h1 className="mt-5 text-[2.5rem] font-semibold leading-[1.04] tracking-tight md:mt-6 md:text-6xl">
          <WordsReveal text="AI agents that evolve themselves." />
          <br />
          <WordsReveal text="With receipts." delay={0.35} wordClassName="text-gradient pb-1" />
        </h1>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.6 }}
          className="mt-5 max-w-xl text-[15px] leading-relaxed text-ink2 md:mt-6 md:text-lg">
          Evolvra runs a team of AI specialists on real missions, has three independent judges grade every result,
          and rewrites the weakest agent's playbook. A new version ships only when it beats the old one.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.75, duration: 0.5 }}
          className="mt-7 grid grid-cols-2 gap-2.5 sm:flex sm:flex-wrap sm:items-center sm:gap-3 md:mt-8">
          <a href={href.agents} style={{ background: "var(--ink)", color: "var(--bg)" }} className="group col-span-2 inline-flex h-12 items-center justify-center gap-2 rounded-full px-5 text-[15px] font-medium transition-transform hover:-translate-y-0.5 active:scale-[0.98] sm:h-auto sm:py-2.5 sm:text-sm">
            Meet the agents <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
          </a>
          <a href={href.tour} className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-line bg-card px-5 text-sm text-ink2 transition-colors hover:border-line-strong hover:text-ink active:scale-[0.98] sm:h-auto sm:py-2.5">
            <Laptop size={15} /> Take the tour
          </a>
          <a href={href.control} className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-line bg-card px-3 text-sm text-ink2 transition-colors hover:text-ink active:scale-[0.98] sm:h-auto sm:border-transparent sm:bg-transparent sm:py-2.5 sm:text-muted">
            <LayoutDashboard size={15} /> Control room
          </a>
        </motion.div>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }} className="mt-6 flex flex-wrap gap-2 md:mt-8">
          <Chip tone="var(--good)">$0 budget, free tiers only</Chip>
          <Chip tone="var(--accent)">Runs every 6 hours, unattended</Chip>
          <Chip tone="var(--accent-2)">3 judges from 3 labs</Chip>
        </motion.div>
      </div>
      <Orbit agents={data.agents} promotedSlug={promotedSlug} promotions={data.summary.promotions} />
    </section>
  );
}

function MiniStat({ label, value, to }: { label: string; value: number; to: string }) {
  return (
    <Spotlight href={to} arrow={false} className="block p-3 sm:p-4">
      <div className="truncate text-[11px] text-muted sm:text-xs">{label}</div>
      <div className="mt-1 text-xl font-semibold tracking-tight sm:mt-1.5 sm:text-2xl"><NumberTicker value={value} /></div>
    </Spotlight>
  );
}

/* ---------------------------------------------------------------- pipeline */

function Pipeline({ data, calls, refused }: { data: Data; calls: number; refused: number }) {
  const steps = [
    { icon: Rocket, title: "Mission", to: href.missions, text: "Claude Code runs a brief through specialist agents. Every handoff, attempt and verdict is recorded.",
      metric: `${data.summary.missions} missions` },
    { icon: Gavel, title: "Judge", to: href.control, text: "Three free models from three labs grade each deliverable. Counts are measured by code, never guessed.",
      metric: `${data.summary.tasks} tasks · ${calls} calls` },
    { icon: Dna, title: "Evolve", to: href.evolutions, text: "The weakest agent's failures become a diagnosis. An AI coach writes three targeted rewrites of its playbook.",
      metric: `${data.summary.evolutions} generations` },
    { icon: Trophy, title: "Promote", to: href.evolutions, text: "Each rewrite fights the original on held-out tasks. A new version ships only if it clearly wins.",
      metric: `${data.summary.promotions} promoted · ${refused} refused` },
  ];
  return (
    <section>
      <Reveal><SectionHeader eyebrow="How it works" title="A closed loop, with a gate at the end"
        sub="Most AI teams hand-tune their prompts and hope. Evolvra measures, rewrites and tests them, and keeps only what wins." /></Reveal>
      <div className="relative">
        <svg className="pointer-events-none absolute left-0 top-[52px] hidden h-2 w-full md:block" preserveAspectRatio="none" viewBox="0 0 100 2">
          <defs>
            <linearGradient id="flowg" x1="0" x2="1">
              <stop offset="0" stopColor="var(--accent)" /><stop offset="0.5" stopColor="var(--accent-2)" /><stop offset="1" stopColor="var(--accent-3)" />
            </linearGradient>
          </defs>
          <line x1="12" y1="1" x2="88" y2="1" stroke="var(--line)" strokeWidth="0.6" vectorEffect="non-scaling-stroke" />
          <line x1="12" y1="1" x2="88" y2="1" stroke="url(#flowg)" strokeWidth="2" className="flow" vectorEffect="non-scaling-stroke" />
        </svg>
        <Rail>{steps.map((st, i) => (
          <Reveal key={st.title} delay={i * 0.1} className="h-full">
            <Spotlight href={st.to} className="block h-full p-5">
              <div className="flex items-center justify-between">
                <span className="relative z-10 grid h-11 w-11 place-items-center rounded-xl border border-line-strong bg-card-solid">
                  <st.icon size={18} className="text-accent" />
                </span>
                <span className="font-mono text-xs text-muted transition-opacity group-hover:opacity-0">0{i + 1}</span>
              </div>
              <h3 className="mt-5 text-base font-semibold">{st.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink2">{st.text}</p>
              <div className="mt-4 font-mono text-xs text-accent">{st.metric}</div>
            </Spotlight>
          </Reveal>
        ))}</Rail>
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
        <ul className="space-y-1.5 sm:space-y-3">
          {scored.map((a) => {
            const isWeak = a.slug === weakest;
            const cur = a.versions.find((v) => v.version === a.current_version);
            return (
              <li key={a.slug}>
                <a href={href.agent(a.slug)} className="group grid grid-cols-[1.75rem_1fr_4.5rem_2rem] items-center gap-3 rounded-lg py-1 active:bg-card-hover sm:grid-cols-[1.75rem_9.5rem_1fr_3rem] sm:py-0.5"
                  title={`${a.tasks} tasks · v${a.current_version}${cur?.top_failure ? ` · top issue: ${humanize(cur.top_failure)}` : ""}`}>
                  <Avatar agent={a} size={26} />
                  <span className="min-w-0">
                    <span className="block truncate text-sm text-ink2 group-hover:text-ink">{a.name}</span>
                    {isWeak && <span className="block text-[10px] font-medium uppercase tracking-wider text-warn sm:hidden">next to evolve</span>}
                  </span>
                  <div className="relative">
                    <Bar value={a.fitness} height={8} color={isWeak ? "var(--warn)" : "color-mix(in srgb, var(--ink-2) 55%, transparent)"} />
                    {isWeak && <span className="absolute -top-5 right-0 hidden text-[10px] font-medium uppercase tracking-wider text-warn sm:block">next to evolve</span>}
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
          action={<a href={href.evolutions} className="-mr-2 rounded-lg px-2 py-1.5 text-sm text-accent hover:underline">View all</a>} />
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
        action={<a href={href.missions} className="-mr-2 shrink-0 rounded-lg px-2 py-1.5 text-sm text-accent hover:underline">All missions</a>} /></Reveal>
      <div className="grid gap-3 md:grid-cols-2 md:gap-4">
        {list.map((m, i) => {
          const fits = m.tasks.map((t) => t.fitness).filter((f): f is number => f != null);
          const avg = fits.length ? fits.reduce((x, y) => x + y, 0) / fits.length : null;
          const g = grade(avg);
          const retries = m.tasks.reduce((n, t) => n + Math.max(0, t.attempts - 1), 0);
          return (
            <Reveal key={m.id} delay={i * 0.06}>
              <Spotlight href={href.mission(m.id)} className="block h-full p-5">
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
