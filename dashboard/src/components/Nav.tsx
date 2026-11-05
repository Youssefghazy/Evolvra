import { motion } from "motion/react";
import { Monitor, Moon, Search, Sun } from "lucide-react";
import { relTime, type Data } from "../data";
import { href, type Route } from "../lib/router";
import { GithubIcon, Kbd } from "./ui";

const LINKS = [["home", "Overview", href.home], ["agents", "Agents", href.agents], ["missions", "Missions", href.missions],
  ["evolutions", "Evolution", href.evolutions]] as const;

export default function Nav({ route, data, theme, setTheme, openPalette }: {
  route: Route; data: Data | null; theme: string; setTheme: (t: string) => void; openPalette: () => void;
}) {
  const active = route.view === "agent" ? "agents" : route.view;
  const nextTheme = theme === "" ? "light" : theme === "light" ? "dark" : "";
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  return (
    <header className="glass sticky top-0 z-40 border-b border-line">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 md:gap-4">
        <a href={href.home} className="flex items-center gap-2 pr-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 place-items-center rounded-lg text-sm"
            style={{ background: "linear-gradient(135deg, var(--accent), var(--accent-2) 55%, var(--accent-3))" }}>🧬</span>
          <span className="hidden sm:inline">Evolvra</span>
        </a>
        <nav className="flex min-w-0 items-center gap-0.5 overflow-x-auto text-sm [scrollbar-width:none]">
          {LINKS.map(([key, label, to]) => (
            <a key={key} href={to} className={`relative rounded-full px-3 py-1.5 transition-colors ${active === key ? "text-ink" : "text-muted hover:text-ink"}`}>
              {active === key && (
                <motion.span layoutId="nav-pill" className="absolute inset-0 rounded-full border border-line bg-card-hover"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }} />
              )}
              <span className="relative">{label}</span>
            </a>
          ))}
        </nav>
        <div className="ml-auto flex shrink-0 items-center gap-1.5 md:gap-2">
          {data && (
            <span className="hidden items-center gap-2 text-xs text-muted lg:inline-flex" title={new Date(data.summary.generated_at).toLocaleString()}>
              <span className="pulse-dot h-1.5 w-1.5 rounded-full text-good" style={{ background: "var(--good)" }} />
              Live · updated {relTime(data.summary.generated_at)}
            </span>
          )}
          <button onClick={openPalette} className="hidden items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-muted transition-colors hover:text-ink md:inline-flex">
            <Search size={13} /> Search <Kbd>Ctrl K</Kbd>
          </button>
          <button onClick={openPalette} aria-label="Search" className="rounded-full border border-line bg-card p-2 text-muted md:hidden"><Search size={14} /></button>
          <button onClick={() => setTheme(nextTheme)} aria-label={`Theme: ${theme || "system"}`} title={`Theme: ${theme || "system"}`}
            className="rounded-full border border-line bg-card p-2 text-muted transition-colors hover:text-ink"><ThemeIcon size={14} /></button>
          <a href="https://github.com/Youssefghazy/Evolvra" target="_blank" rel="noreferrer" aria-label="GitHub"
            className="hidden rounded-full border border-line bg-card p-2 text-muted transition-colors hover:text-ink sm:inline-flex"><GithubIcon size={14} /></a>
        </div>
      </div>
    </header>
  );
}
