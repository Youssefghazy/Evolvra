import { useRef, useState, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import {
  Bot, CheckCircle2, CircleDashed, Clock3, Code2, Gauge, ListOrdered, Megaphone, PenTool, ScanSearch, Server,
  ShieldCheck, TrendingUp, Workflow, XCircle, Zap, type LucideIcon,
} from "lucide-react";
import { divisionColor, grade, toneVar, type Agent } from "../data";

export function SectionHeader({ eyebrow, title, action, sub }: { eyebrow?: string; title: ReactNode; action?: ReactNode; sub?: ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4 md:mb-5">
      <div className="min-w-0">
        {eyebrow && <div className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.18em] text-muted">{eyebrow}</div>}
        <h2 className="text-xl font-semibold tracking-tight md:text-2xl">{title}</h2>
        {sub && <p className="mt-1 max-w-2xl text-sm text-ink2">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

export function Chip({ children, tone, className = "", title }: { children: ReactNode; tone?: string; className?: string; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-2.5 py-0.5 text-[11px] font-medium text-ink2 ${className}`}>
      {tone && <span className="h-1.5 w-1.5 rounded-full" style={{ background: tone }} />}
      {children}
    </span>
  );
}

export function DivisionChip({ division }: { division: string }) {
  return <Chip tone={divisionColor(division)}>{division.replace("-", " ")}</Chip>;
}

/** One line-icon per role, so the roster reads like a team, not a sticker sheet. */
const ROLE_ICONS: Record<string, LucideIcon> = {
  "frontend-developer": Code2, "backend-architect": Server, "devops-automator": Workflow, "rapid-prototyper": Zap,
  "ux-researcher": ScanSearch, "content-creator": PenTool, "growth-hacker": TrendingUp, "sprint-prioritizer": ListOrdered,
  "evidence-collector": Gauge, "reality-checker": ShieldCheck,
};
const DIVISION_ICONS: Record<string, LucideIcon> = { engineering: Code2, marketing: Megaphone, testing: ShieldCheck };

export function roleIcon(agent: { slug?: string; name: string; division: string }): LucideIcon {
  const slug = agent.slug ?? agent.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  return ROLE_ICONS[slug] ?? DIVISION_ICONS[agent.division] ?? Bot;
}

export function Avatar({ agent, size = 40, ring = false }: {
  agent: Pick<Agent, "division" | "name"> & { slug?: string }; size?: number; ring?: boolean;
}) {
  const c = divisionColor(agent.division);
  const Icon = roleIcon(agent);
  return (
    <span className="relative inline-grid shrink-0 place-items-center"
      style={{
        width: size, height: size, borderRadius: size * 0.3,
        background: `linear-gradient(145deg, color-mix(in srgb, ${c} 34%, var(--card-solid)), color-mix(in srgb, ${c} 10%, var(--card-solid)))`,
        boxShadow: `inset 0 1px 0 rgba(255,255,255,0.10), inset 0 0 0 1px color-mix(in srgb, ${c} 45%, transparent)${ring ? `, 0 0 0 3px var(--bg), 0 0 22px -2px ${c}` : ""}`,
      }}
      aria-label={agent.name} title={agent.name}>
      <Icon size={Math.round(size * 0.5)} strokeWidth={1.75} style={{ color: `color-mix(in srgb, ${c} 55%, white)` }} />
    </span>
  );
}

/** Radial fitness gauge. The number is always printed, so color is never the only channel. */
export function Ring({ value, size = 64, stroke = 6, label = true }: { value: number | null; size?: number; stroke?: number; label?: boolean }) {
  const reduce = useReducedMotion();
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const g = grade(value);
  const frac = value ?? 0;
  return (
    <span className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={stroke} />
        <motion.circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={toneVar[g.tone]} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c}
          initial={reduce ? false : { strokeDashoffset: c }}
          whileInView={{ strokeDashoffset: c * (1 - frac) }}
          viewport={{ once: true }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          style={reduce ? { strokeDashoffset: c * (1 - frac) } : undefined} />
      </svg>
      {label && (
        <span className="absolute font-mono font-semibold tnum" style={{ fontSize: size * 0.24 }}>
          {value == null ? "–" : Math.round(value * 100)}
        </span>
      )}
    </span>
  );
}

/** Thin horizontal bar, 4px rounded data end, recessive track. */
export function Bar({ value, color = "var(--ink-2)", height = 6, className = "" }: { value: number | null; color?: string; height?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <div className={`w-full overflow-hidden rounded-full bg-line ${className}`} style={{ height }}>
      <motion.div className="h-full rounded-full" style={{ background: color }}
        initial={reduce ? false : { width: 0 }}
        whileInView={{ width: `${Math.max(0, Math.min(1, value ?? 0)) * 100}%` }}
        viewport={{ once: true }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }} />
    </div>
  );
}

export function Verdict({ v, compact = false }: { v: string | null | undefined; compact?: boolean }) {
  const map: Record<string, { icon: ReactNode; color: string; label: string }> = {
    PASS: { icon: <CheckCircle2 size={14} />, color: "var(--good)", label: "Pass" },
    DONE: { icon: <CheckCircle2 size={14} />, color: "var(--good)", label: "Done" },
    FAIL: { icon: <XCircle size={14} />, color: "var(--bad)", label: "Fail" },
    FAILED: { icon: <XCircle size={14} />, color: "var(--bad)", label: "Failed" },
    NEEDS_WORK: { icon: <CircleDashed size={14} />, color: "var(--warn)", label: "Needs work" },
    ESCALATED: { icon: <XCircle size={14} />, color: "var(--warn)", label: "Escalated" },
    RUNNING: { icon: <Clock3 size={14} />, color: "var(--accent)", label: "Running" },
  };
  const m = map[(v ?? "").toUpperCase()] ?? { icon: <CircleDashed size={14} />, color: "var(--muted)", label: v ?? "–" };
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: m.color }}>
      {m.icon}{!compact && <span className="text-ink2">{m.label}</span>}
    </span>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd className="rounded-md border border-line bg-card px-1.5 py-0.5 font-mono text-[10px] text-muted">{children}</kbd>;
}

export function Empty({ title, hint, icon }: { title: string; hint: string; icon?: ReactNode }) {
  return (
    <div className="surface grid place-items-center px-6 py-16 text-center">
      {icon && <div className="mb-3 text-muted">{icon}</div>}
      <div className="text-lg font-medium">{title}</div>
      <div className="mt-2 max-w-md text-sm text-ink2">{hint}</div>
    </div>
  );
}

export function Stat({ label, children, sub, icon }: { label: string; children: ReactNode; sub?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="surface p-4 md:p-5">
      <div className="flex items-center justify-between text-xs text-muted">{label}{icon}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight md:text-3xl">{children}</div>
      {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
    </div>
  );
}

/** GitHub mark (lucide dropped brand icons). */
export function GithubIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.53-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a10.9 10.9 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
    </svg>
  );
}

/**
 * Swipe rail on phones, plain grid from md up. Cards snap into place, the next one peeks in so the
 * gesture is obvious, and dots underneath track which card is in view.
 */
export function Rail({ children, cols = "md:grid-cols-4", className = "" }: { children: ReactNode[]; cols?: string; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [at, setAt] = useState(0);
  const onScroll = () => {
    const el = ref.current; if (!el) return;
    const w = (el.firstElementChild as HTMLElement | null)?.offsetWidth ?? el.clientWidth;
    setAt(Math.round(el.scrollLeft / (w + 12)));
  };
  return (
    <div className={className}>
      <div ref={ref} onScroll={onScroll}
        className={`no-scrollbar -mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-px-4 px-4 pb-1 md:mx-0 md:grid md:gap-4 md:overflow-visible md:px-0 md:pb-0 ${cols}`}>
        {children.map((c, i) => <div key={i} className="w-[84%] shrink-0 snap-start md:w-auto">{c}</div>)}
      </div>
      <div className="mt-3 flex justify-center gap-1.5 md:hidden" aria-hidden>
        {children.map((_, i) => (
          <span key={i} className="h-1.5 rounded-full transition-all duration-300"
            style={{ width: i === at ? 18 : 6, background: i === at ? "var(--accent)" : "var(--line-strong)" }} />
        ))}
      </div>
    </div>
  );
}
