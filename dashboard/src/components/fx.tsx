import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { animate, motion, useInView, useReducedMotion } from "motion/react";
import { ArrowUpRight } from "lucide-react";
import { coarsePointer } from "../lib/media";

/** Fixed page backdrop: masked grid + slow aurora. Pure CSS, GPU-cheap. */
export function Backdrop() {
  return (
    <>
      <div className="backdrop-grid" />
      <div className="aurora" aria-hidden><span /><span /><span /></div>
    </>
  );
}

/**
 * Surface card. One rule for the whole site: if it has an `href` it is a link and looks like one
 * (glow follows the cursor, border lights, card lifts, an arrow appears, pointer cursor, focus ring);
 * without an `href` it is a static panel and does not react to hover at all.
 */
export function Spotlight({ children, className = "", href, style, arrow = true }: {
  children: ReactNode; className?: string; as?: "div" | "a"; href?: string; style?: CSSProperties; arrow?: boolean;
}) {
  const ref = useRef<HTMLAnchorElement | null>(null);
  if (!href) return <div className={`relative overflow-hidden surface ${className}`} style={style}>{children}</div>;
  const onMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`);
    el.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  const external = /^https?:/.test(href);
  return (
    <a ref={ref} href={href} onMouseMove={onMove} style={style} target={external ? "_blank" : undefined} rel={external ? "noreferrer" : undefined}
      className={`group relative cursor-pointer overflow-hidden surface outline-none transition-[transform,border-color,box-shadow] duration-200 hover:-translate-y-0.5 hover:border-line-strong active:scale-[0.985] focus-visible:ring-2 [-webkit-tap-highlight-color:transparent] focus-visible:ring-accent ${className}`}>
      <span aria-hidden className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: "radial-gradient(420px circle at var(--mx, 50%) var(--my, 0%), var(--glow), transparent 45%)" }} />
      {arrow && (
        <span aria-hidden className="pointer-events-none absolute right-3 top-3 z-10 grid h-7 w-7 translate-x-1 -translate-y-1 place-items-center rounded-full border border-line bg-card-solid text-muted opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:translate-y-0 group-hover:text-ink group-hover:opacity-100">
          <ArrowUpRight size={14} />
        </span>
      )}
      <div className="relative">{children}</div>
    </a>
  );
}

/** Fade-and-rise on first view. Staggers children when used as a list via `delay`. */
export function Reveal({ children, delay = 0, className = "", y = 14 }: {
  children: ReactNode; delay?: number; className?: string; y?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : coarsePointer ? { opacity: 0, y } : { opacity: 0, y, filter: "blur(6px)" }}
      whileInView={coarsePointer ? { opacity: 1, y: 0 } : { opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/** Counts up from 0 when it scrolls into view. */
export function NumberTicker({ value, decimals = 0, prefix = "", suffix = "", className = "" }: {
  value: number; decimals?: number; prefix?: string; suffix?: string; className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const reduce = useReducedMotion();
  const fmt = (n: number) => `${prefix}${n.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;
  useEffect(() => {
    const el = ref.current;
    if (!el || !inView) return;
    if (reduce) { el.textContent = fmt(value); return; }
    const controls = animate(0, value, { duration: 1.4, ease: [0.16, 1, 0.3, 1], onUpdate: (v) => { el.textContent = fmt(v); } });
    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, value]);
  return <span ref={ref} className={`tnum ${className}`}>{fmt(reduce ? value : 0)}</span>;
}

/** Text that appears word by word. */
export function WordsReveal({ text, className = "", wordClassName = "", delay = 0 }: {
  text: string; className?: string; wordClassName?: string; delay?: number;
}) {
  const reduce = useReducedMotion();
  // gradient text must sit on each animated word: Chrome drops background-clip:text through transformed children
  return (
    <span className={className}>
      {text.split(" ").map((w, i) => (
        <motion.span key={i} className={`inline-block ${wordClassName}`}
          initial={reduce ? false : { opacity: 0, y: 12, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.5, delay: delay + i * 0.06, ease: [0.22, 1, 0.36, 1] }}>
          {w}&nbsp;
        </motion.span>
      ))}
    </span>
  );
}
