import { useId } from "react";

/**
 * Evolvra mark, drawn in the current text color so it belongs to whichever theme is on:
 * an "E" whose three strokes grow as they rise (each generation longer than the last), a spine with a
 * slight helix bend, and one accent node at the tip of the top stroke: the promotion.
 */
export function LogoMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} role="img" aria-label="Evolvra" fill="none">
      <defs>
        <linearGradient id={`n-${id}`} x1="20" y1="13" x2="27" y2="6" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="var(--accent)" />
          <stop offset="1" stopColor="var(--accent-2)" />
        </linearGradient>
      </defs>
      <rect x="1.25" y="1.25" width="29.5" height="29.5" rx="9" fill="currentColor" fillOpacity="0.06" stroke="currentColor" strokeOpacity="0.16" />
      <g stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
        <path d="M10 9.5 C 8.7 13, 11.3 16, 10 22.5" />
        <path d="M10 22.5 H 15.5" strokeOpacity="0.9" />
        <path d="M10.6 16 H 17.5" strokeOpacity="0.95" />
        <path d="M10 9.5 H 19.5" />
      </g>
      <circle cx="23" cy="9.5" r="4.2" fill={`url(#n-${id})`} fillOpacity="0.22" />
      <circle cx="23" cy="9.5" r="2.2" fill={`url(#n-${id})`} />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2 text-ink">
      <LogoMark size={size} />
      <span className="text-[15px] font-semibold tracking-tight">Evolvra</span>
    </span>
  );
}
