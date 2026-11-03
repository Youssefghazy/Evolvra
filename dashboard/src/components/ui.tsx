import type { ReactNode } from "react";
import { fitnessColor, pct } from "../data";

export function Card({ title, children, right, className = "" }: { title?: ReactNode; children: ReactNode; right?: ReactNode; className?: string }) {
  return (
    <section className={`panel p-4 ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium muted uppercase tracking-wide">{title}</h2>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="panel p-4">
      <div className="text-xs muted">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
      {sub && <div className="text-xs muted mt-1">{sub}</div>}
    </div>
  );
}

export function Fitness({ value, width = 96 }: { value: number | null | undefined; width?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="bar" style={{ width }}><span style={{ width: `${Math.round((value ?? 0) * 100)}%` }} /></span>
      <span className="mono text-xs" style={{ color: fitnessColor(value) }}>{pct(value)}</span>
    </span>
  );
}

export function Verdict({ v }: { v: string | null | undefined }) {
  const color = v === "PASS" ? "var(--good)" : v === "FAIL" ? "var(--bad)" : v ? "var(--warn)" : "var(--muted)";
  return <span className="chip" style={{ color }}>{v ?? "–"}</span>;
}

export function Badge({ children, color }: { children: ReactNode; color?: string }) {
  return <span className="chip" style={color ? { borderColor: color, color } : undefined}>{children}</span>;
}
