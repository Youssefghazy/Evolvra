/**
 * Page links with a gliding highlight. A soft pill rests under the current page and slides to
 * whichever link the pointer (or keyboard focus) is on, then glides back when it leaves. The current
 * page also keeps a short accent bar, so "where am I" and "what will I click" never look the same.
 */
import { motion, useReducedMotion } from "motion/react";
import { useState, type ReactNode } from "react";
import { cn } from "../../lib/utils";

export type NavLink = { key: string; name: string; link: string; icon?: ReactNode; active?: boolean };

export function NavLinks({ id, items, compact = false, className }: {
  id: string; items: NavLink[]; compact?: boolean; className?: string;
}) {
  const reduce = useReducedMotion();
  const [hover, setHover] = useState<string | null>(null);
  const current = items.find((i) => i.active)?.key ?? null;
  const target = hover ?? current;
  const spring = reduce ? { duration: 0 } : { type: "spring" as const, stiffness: 420, damping: 34, mass: 0.7 };
  return (
    <nav className={cn("relative flex items-center", className)} onMouseLeave={() => setHover(null)}>
      {items.map((it) => (
        <a key={it.key} href={it.link} aria-current={it.active ? "page" : undefined}
          onMouseEnter={() => setHover(it.key)} onFocus={() => setHover(it.key)} onBlur={() => setHover(null)}
          className={cn(
            "relative flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm outline-none transition-colors duration-200",
            "focus-visible:ring-2 focus-visible:ring-accent",
            target === it.key || it.active ? "text-ink" : "text-muted",
          )}>
          {target === it.key && (
            <motion.span layoutId={`${id}-pill`} transition={spring} aria-hidden
              className={cn("absolute inset-0 -z-0 rounded-full border bg-card-hover",
                hover && hover !== current ? "border-line-strong" : "border-line")}
              style={{ boxShadow: hover && hover !== current ? "0 0 0 1px var(--glow), 0 6px 20px -8px var(--glow)" : undefined }} />
          )}
          {it.active && (
            <motion.span layoutId={`${id}-bar`} transition={spring} aria-hidden
              className="absolute inset-x-3 -bottom-px h-px rounded-full"
              style={{ background: "linear-gradient(90deg, transparent, var(--accent), transparent)" }} />
          )}
          {it.icon && <span className={cn("relative grid place-items-center transition-transform duration-200", target === it.key && "scale-110", compact ? "block sm:hidden" : "")}>{it.icon}</span>}
          <span className={cn("relative whitespace-nowrap", compact && "hidden sm:block")}>{it.name}</span>
        </a>
      ))}
    </nav>
  );
}
