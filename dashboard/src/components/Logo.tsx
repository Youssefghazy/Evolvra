import { useId } from "react";

/**
 * Evolvra mark: an "E" whose three strokes grow as they rise (each generation longer than the last),
 * joined by a spine with a slight helix bend, and a node at the tip of the top stroke for the promotion.
 */
export function LogoMark({ size = 28, className = "" }: { size?: number; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" className={className} role="img" aria-label="Evolvra">
      <defs>
        <linearGradient id={`g-${id}`} x1="0" y1="32" x2="32" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="0.55" stopColor="#a78bfa" />
          <stop offset="1" stopColor="#f472b6" />
        </linearGradient>
        <radialGradient id={`s-${id}`} cx="0.3" cy="0.2" r="0.9">
          <stop offset="0" stopColor="#fff" stopOpacity="0.35" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect x="1" y="1" width="30" height="30" rx="9" fill={`url(#g-${id})`} />
      <rect x="1" y="1" width="30" height="30" rx="9" fill={`url(#s-${id})`} />
      <rect x="1.5" y="1.5" width="29" height="29" rx="8.5" fill="none" stroke="#fff" strokeOpacity="0.22" />
      <g stroke="#fff" strokeWidth="2.6" strokeLinecap="round" fill="none">
        <path d="M10 9.5 C 8.6 13, 11.4 16, 10 22.5" />
        <path d="M10 22.5 H 15.5" strokeOpacity="0.72" />
        <path d="M10.6 16 H 18.5" strokeOpacity="0.86" />
        <path d="M10 9.5 H 20.5" />
      </g>
      <circle cx="23.4" cy="9.5" r="2.1" fill="#fff" />
      <circle cx="23.4" cy="9.5" r="3.6" fill="#fff" fillOpacity="0.22" />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark size={size} />
      <span className="text-[15px] font-semibold tracking-tight">Evolvra</span>
    </span>
  );
}
