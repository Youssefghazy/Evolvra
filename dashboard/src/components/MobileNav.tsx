/**
 * Phone navigation. Desktop gets the floating dock; a phone gets what phone users already know:
 * a bottom tab bar within thumb reach (five main pages, labelled, 56 px tall, safe-area aware)
 * and a menu sheet for everything else (Tour, theme, GitHub). Both are hidden from md up.
 */
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, type ReactNode } from "react";
import { Bot, ChevronRight, Dna, Home, LayoutDashboard, Laptop, Moon, Rocket, Search, Sun, X } from "lucide-react";
import { href } from "../lib/router";
import { GithubIcon } from "./ui";
import { LogoMark } from "./Logo";

const tabs = [
  { key: "home", name: "Overview", link: href.home, Icon: Home },
  { key: "control", name: "Control", link: href.control, Icon: LayoutDashboard },
  { key: "agents", name: "Agents", link: href.agents, Icon: Bot },
  { key: "missions", name: "Missions", link: href.missions, Icon: Rocket },
  { key: "evolutions", name: "Evolution", link: href.evolutions, Icon: Dna },
];

export function MobileTabBar({ active }: { active: string }) {
  const reduce = useReducedMotion();
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-50 border-t border-line bg-card-solid/90 backdrop-blur-xl md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
      <ul className="mx-auto grid max-w-md grid-cols-5">
        {tabs.map(({ key, name, link, Icon }) => {
          const on = active === key;
          return (
            <li key={key}>
              <a href={link} aria-current={on ? "page" : undefined}
                className="relative flex h-14 flex-col items-center justify-center gap-1 text-[10.5px] font-medium outline-none [-webkit-tap-highlight-color:transparent] focus-visible:bg-card-hover active:scale-95 transition-transform"
                style={{ color: on ? "var(--ink)" : "var(--muted)" }}>
                {on && <motion.span layoutId="tab-glow" transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 38 }}
                  className="absolute top-0 h-0.5 w-8 rounded-full" style={{ background: "var(--accent)", boxShadow: "0 0 12px var(--accent)" }} />}
                <Icon size={20} strokeWidth={on ? 2.1 : 1.75} style={{ color: on ? "var(--accent)" : undefined }} />
                {name}
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function MobileMenu({ open, onClose, active, theme, toggleTheme, openPalette }: {
  open: boolean; onClose: () => void; active: string; theme: "dark" | "light"; toggleTheme: () => void; openPalette: () => void;
}) {
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => { document.body.style.overflow = prev; window.removeEventListener("keydown", onKey); };
  }, [open, onClose]);
  const pages = [...tabs, { key: "tour", name: "Tour", link: href.tour, Icon: Laptop }];
  const desc: Record<string, string> = {
    home: "Live status and the latest promotion", control: "KPIs, quality, judges, activity", agents: "The roster and their fitness",
    missions: "Every task, attempt and verdict", evolutions: "Every generation, promoted or refused", tour: "Replay a real mission",
  };
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[80] md:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: reduce ? 0 : 0.18 }}>
          <button aria-label="Close menu" onClick={onClose} className="absolute inset-0 bg-black/55 backdrop-blur-sm" />
          <motion.div role="dialog" aria-modal="true" aria-label="Menu"
            initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
            transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 380, damping: 36 }}
            drag={reduce ? false : "y"} dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, i) => { if (i.offset.y > 90 || i.velocity.y > 500) onClose(); }}
            className="absolute inset-x-0 bottom-0 max-h-[85vh] overflow-y-auto rounded-t-3xl border-t border-line-strong bg-card-solid px-4 pt-2"
            style={{ paddingBottom: "calc(env(safe-area-inset-bottom) + 16px)" }}>
            <div className="mx-auto mb-3 mt-1 h-1 w-10 rounded-full bg-line-strong" aria-hidden />
            <div className="mb-3 flex items-center justify-between">
              <span className="inline-flex items-center gap-2 font-semibold text-ink"><LogoMark size={22} /> Evolvra</span>
              <button onClick={onClose} aria-label="Close menu" className="grid h-10 w-10 place-items-center rounded-full border border-line text-muted active:bg-card-hover"><X size={18} /></button>
            </div>
            <button onClick={() => { onClose(); openPalette(); }}
              className="mb-3 flex h-12 w-full items-center gap-3 rounded-2xl border border-line bg-card px-4 text-sm text-muted active:bg-card-hover">
              <Search size={16} /> Search agents and missions
            </button>
            <ul className="overflow-hidden rounded-2xl border border-line">
              {pages.map(({ key, name, link, Icon }) => (
                <li key={key} className="border-b border-line last:border-0">
                  <a href={link} onClick={onClose} className="flex min-h-[56px] items-center gap-3 px-4 py-2 active:bg-card-hover"
                    aria-current={active === key ? "page" : undefined}>
                    <span className="grid h-9 w-9 place-items-center rounded-xl border border-line"
                      style={{ color: active === key ? "var(--accent)" : "var(--ink-2)", background: active === key ? "var(--glow)" : undefined }}><Icon size={17} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-ink">{name}</span>
                      <span className="block truncate text-xs text-muted">{desc[key]}</span>
                    </span>
                    <ChevronRight size={16} className="text-muted" />
                  </a>
                </li>
              ))}
            </ul>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <SheetButton onClick={toggleTheme} icon={theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}>{theme === "dark" ? "Light mode" : "Dark mode"}</SheetButton>
              <SheetButton href="https://github.com/Youssefghazy/Evolvra" icon={<GithubIcon size={16} />}>GitHub</SheetButton>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function SheetButton({ children, icon, onClick, href: to }: { children: ReactNode; icon: ReactNode; onClick?: () => void; href?: string }) {
  const cls = "flex h-12 items-center justify-center gap-2 rounded-2xl border border-line bg-card text-sm font-medium text-ink active:bg-card-hover";
  return to ? <a href={to} target="_blank" rel="noreferrer" className={cls}>{icon}{children}</a>
    : <button onClick={onClick} className={cls}>{icon}{children}</button>;
}
