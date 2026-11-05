import { useMemo, useState } from "react";
import {
  AnimatePresence, motion, useAnimationFrame, useMotionValue, useReducedMotion, useSpring, useTransform, type MotionValue,
} from "motion/react";
import { grade, pct, toneVar, type Agent } from "../data";
import { href } from "../lib/router";
import { LogoMark } from "./Logo";
import { Avatar } from "./ui";

const TILT = 0.52;          // vertical squash: the orbit plane leans away from the viewer
const BASE_SPEED = 0.00012; // radians per ms (~52 s per lap)

/**
 * The roster as a living system: agents travel on two tilted orbits, nearer ones larger and brighter.
 * Hovering eases the motion down to a drift (a spring on speed, never a hard stop) and turns the core
 * into that agent's card.
 */
export default function Orbit({ agents, promotedSlug, promotions }: { agents: Agent[]; promotedSlug?: string; promotions: number }) {
  const reduce = useReducedMotion();
  const angle = useMotionValue(0);
  const target = useMotionValue(1);
  const speed = useSpring(target, { stiffness: 30, damping: 18, mass: 1 });
  const [hover, setHover] = useState<Agent | null>(null);

  useAnimationFrame((_, delta) => {
    if (reduce) return;
    angle.set(angle.get() + Math.min(delta, 50) * BASE_SPEED * speed.get());
  });

  const nodes = useMemo(() => {
    const inner = agents.slice(0, 4), outer = agents.slice(4);
    return [
      ...inner.map((a, i) => ({ a, r: 29, phase: (i / inner.length) * Math.PI * 2 + 0.6, dir: 1 })),
      ...outer.map((a, i) => ({ a, r: 46, phase: (i / outer.length) * Math.PI * 2, dir: -0.7 })),
    ];
  }, [agents]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
      className="relative mx-auto aspect-[1/0.82] w-full max-w-[540px] select-none"
      onMouseEnter={() => target.set(0.22)} onMouseLeave={() => { target.set(1); setHover(null); }}>
      {/* orbit planes */}
      <svg viewBox="0 0 100 82" className="absolute inset-0 h-full w-full overflow-visible" aria-hidden>
        <defs>
          <linearGradient id="orbit-stroke" x1="0" x2="1">
            <stop offset="0" stopColor="var(--accent)" stopOpacity="0.55" />
            <stop offset="0.5" stopColor="var(--accent-2)" stopOpacity="0.15" />
            <stop offset="1" stopColor="var(--accent-3)" stopOpacity="0.55" />
          </linearGradient>
          <radialGradient id="orbit-core">
            <stop offset="0" stopColor="var(--accent-2)" stopOpacity="0.35" />
            <stop offset="1" stopColor="var(--accent-2)" stopOpacity="0" />
          </radialGradient>
        </defs>
        <ellipse cx="50" cy="41" rx="46" ry={46 * TILT} fill="none" stroke="url(#orbit-stroke)" strokeWidth="0.25" />
        <ellipse cx="50" cy="41" rx="29" ry={29 * TILT} fill="none" stroke="url(#orbit-stroke)" strokeWidth="0.25" />
        <ellipse cx="50" cy="41" rx="38" ry={38 * TILT} fill="none" stroke="var(--line)" strokeWidth="0.15" strokeDasharray="0.6 1.4" />
        <circle cx="50" cy="41" r="18" fill="url(#orbit-core)" />
      </svg>

      {/* core: brand at rest, agent card on hover */}
      <div className="absolute left-1/2 top-1/2 z-[5] -translate-x-1/2 -translate-y-1/2">
        <div className="relative grid h-[104px] w-[136px] place-items-center rounded-3xl border border-line-strong bg-card-solid/90 text-center backdrop-blur"
          style={{ boxShadow: "0 0 70px -18px var(--accent-2), inset 0 1px 0 rgba(255,255,255,0.06)" }}>
          <AnimatePresence mode="wait">
            {hover ? (
              <motion.a key={hover.slug} href={href.agent(hover.slug)} className="block px-3"
                initial={{ opacity: 0, y: 6, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                exit={{ opacity: 0, y: -6, filter: "blur(4px)" }} transition={{ duration: 0.22 }}>
                <div className="text-[13px] font-semibold leading-tight">{hover.name}</div>
                <div className="mt-1 font-mono text-2xl font-semibold tnum" style={{ color: toneVar[grade(hover.fitness).tone] }}>{pct(hover.fitness)}</div>
                <div className="text-[10px] uppercase tracking-wider text-muted">fitness · v{hover.current_version} · {hover.tasks} tasks</div>
              </motion.a>
            ) : (
              <motion.div key="brand" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.22 }}>
                <LogoMark size={38} className="mx-auto" />
                <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">{agents.length} agents · {promotions} evolved</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {nodes.map((n) => (
        <OrbitNode key={n.a.slug} {...n} angle={angle} promoted={n.a.slug === promotedSlug}
          active={hover?.slug === n.a.slug} onHover={setHover} />
      ))}
    </motion.div>
  );
}

function OrbitNode({ a, r, phase, dir, angle, promoted, active, onHover }: {
  a: Agent; r: number; phase: number; dir: number; angle: MotionValue<number>; promoted: boolean; active: boolean;
  onHover: (a: Agent | null) => void;
}) {
  const theta = useTransform(angle, (v) => v * dir + phase);
  const left = useTransform(theta, (t) => `${50 + Math.cos(t) * r}%`);
  const top = useTransform(theta, (t) => `${50 + (Math.sin(t) * r * TILT * 100) / 82}%`);
  const depth = useTransform(theta, (t) => (Math.sin(t) + 1) / 2);          // 0 = far, 1 = near
  const scale = useTransform(depth, (d) => 0.72 + d * 0.38);
  const opacity = useTransform(depth, (d) => 0.5 + d * 0.5);
  const zIndex = useTransform(depth, (d) => (d > 0.5 ? 10 : 1));
  const blur = useTransform(depth, (d) => `blur(${(1 - d) * 0.6}px)`);
  return (
    <motion.a href={href.agent(a.slug)} aria-label={a.name}
      onMouseEnter={() => onHover(a)}
      className="absolute -translate-x-1/2 -translate-y-1/2"
      style={{ left, top, scale: active ? 1.25 : scale, opacity: active ? 1 : opacity, zIndex: active ? 20 : zIndex, filter: active ? "none" : blur }}>
      <span className="relative block">
        {promoted && <span className="absolute -inset-2 animate-pulse rounded-[30%]" style={{ boxShadow: "0 0 28px 4px color-mix(in srgb, var(--good) 55%, transparent)" }} />}
        <Avatar agent={a} size={promoted ? 52 : 44} ring={active} />
        {promoted && (
          <span className="absolute -right-2.5 -top-2 rounded-full border border-line bg-card-solid px-1.5 font-mono text-[10px] text-good">v{a.current_version}</span>
        )}
      </span>
    </motion.a>
  );
}
