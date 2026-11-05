import { useId, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

/** Tiny trend line for KPI cards: one series, 2px line, soft fill, endpoint marker. */
export function Sparkline({ values, height = 40, color = "var(--series-1)" }: { values: number[]; height?: number; color?: string }) {
  const id = useId().replace(/:/g, "");
  const reduce = useReducedMotion();
  if (values.length < 2) return <div style={{ height }} />;
  const w = 120, h = height, pad = 3;
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = hi - lo || 1;
  const pts = values.map((v, i) => [pad + (i / (values.length - 1)) * (w - pad * 2), h - pad - ((v - lo) / span) * (h - pad * 2)] as const);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full" style={{ height }} aria-hidden>
      <defs>
        <linearGradient id={`sf-${id}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.28" /><stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${last[0]},${h} L${pts[0][0]},${h} Z`} fill={`url(#sf-${id})`} />
      <motion.path d={d} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }} />
      <circle cx={last[0]} cy={last[1]} r="3" fill={color} stroke="var(--card-solid)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export type Point = { x: number; y: number; label: string; sub: string; href?: string };

/** Area chart with a crosshair + tooltip. Y is a labelled 50-100 window, because every score sits above 50. */
export function AreaChart({ points, height = 260, yMin = 0.5, refLine }: { points: Point[]; height?: number; yMin?: number; refLine?: { y: number; label: string } }) {
  const id = useId().replace(/:/g, "");
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);
  const W = 800, H = height, L = 36, R = 12, T = 12, B = 26;
  const geo = useMemo(() => {
    if (points.length === 0) return null;
    const x0 = points[0].x, x1 = points[points.length - 1].x || x0 + 1;
    const sx = (x: number) => L + ((x - x0) / Math.max(1, x1 - x0)) * (W - L - R);
    const sy = (y: number) => T + (1 - (Math.max(yMin, Math.min(1, y)) - yMin) / (1 - yMin)) * (H - T - B);
    const xy = points.map((p) => [sx(p.x), sy(p.y)] as const);
    const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const area = `${line} L${xy[xy.length - 1][0]},${H - B} L${xy[0][0]},${H - B} Z`;
    return { sx, sy, xy, line, area };
  }, [points, H, yMin]);
  if (!geo) return <div className="grid h-40 place-items-center text-sm text-muted">No data yet.</div>;
  const ticks = [yMin, yMin + (1 - yMin) / 2, 1];
  const onMove = (e: React.MouseEvent) => {
    const r = ref.current?.getBoundingClientRect(); if (!r) return;
    const x = ((e.clientX - r.left) / r.width) * W;
    let best = 0, bd = Infinity;
    geo.xy.forEach(([px], i) => { const d = Math.abs(px - x); if (d < bd) { bd = d; best = i; } });
    setHover(best);
  };
  const hp = hover != null ? geo.xy[hover] : null;
  return (
    <div ref={ref} className="relative" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }} preserveAspectRatio="none" role="img" aria-label="Mission quality over time">
        <defs>
          <linearGradient id={`af-${id}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--series-1)" stopOpacity="0.32" /><stop offset="1" stopColor="var(--series-1)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={geo.sy(t)} y2={geo.sy(t)} stroke="var(--line)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <text x={L - 8} y={geo.sy(t) + 4} textAnchor="end" fontSize="11" fill="var(--muted)" className="tnum">{Math.round(t * 100)}</text>
          </g>
        ))}
        {refLine && (
          <g>
            <line x1={L} x2={W - R} y1={geo.sy(refLine.y)} y2={geo.sy(refLine.y)} stroke="var(--good)" strokeOpacity="0.5" strokeWidth="1" vectorEffect="non-scaling-stroke" />
            <text x={L + 6} y={geo.sy(refLine.y) - 5} textAnchor="start" fontSize="10" fill="var(--good)">{refLine.label}</text>
          </g>
        )}
        <motion.path d={geo.area} fill={`url(#af-${id})`} initial={reduce ? false : { opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.8, delay: 0.4 }} />
        <motion.path d={geo.line} fill="none" stroke="var(--series-1)" strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinejoin="round"
          initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }} />
        {hp && <line x1={hp[0]} x2={hp[0]} y1={T} y2={H - B} stroke="var(--line-strong)" strokeWidth="1" vectorEffect="non-scaling-stroke" />}
      </svg>
      {/* markers in HTML so they stay round under preserveAspectRatio=none */}
      {geo.xy.map(([x, y], i) => (
        <span key={i} className="pointer-events-none absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ left: `${(x / W) * 100}%`, top: `${(y / H) * height}px`, background: hover === i ? "var(--series-1)" : "var(--card-solid)",
            boxShadow: `0 0 0 2px var(--series-1)${hover === i ? ", 0 0 0 6px color-mix(in srgb, var(--series-1) 25%, transparent)" : ""}` }} />
      ))}
      {hover != null && hp && (
        <div className="pointer-events-none absolute z-10 w-64 -translate-y-full rounded-xl border border-line-strong bg-card-solid p-3 text-xs shadow-2xl"
          style={{ left: `clamp(0px, calc(${(hp[0] / W) * 100}% - 8rem), calc(100% - 16rem))`, top: `${(hp[1] / H) * height - 14}px` }}>
          <div className="font-mono text-lg font-semibold tnum">{Math.round(points[hover].y * 100)}%</div>
          <div className="mt-1 line-clamp-2 text-ink2">{points[hover].label}</div>
          <div className="mt-1 text-muted">{points[hover].sub}</div>
        </div>
      )}
    </div>
  );
}
