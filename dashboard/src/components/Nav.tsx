import { Bot, Dna, Home, LayoutDashboard, Laptop, Monitor, Moon, Rocket, Search, Sun } from "lucide-react";
import { relTime, type Data } from "../data";
import { href, type Route } from "../lib/router";
import { FloatingDock, type DockItem } from "./ui/floating-dock";
import { Logo } from "./Logo";
import { GithubIcon, Kbd } from "./ui";

const ic = "h-full w-full text-neutral-500 dark:text-neutral-300";

/** Slim top bar (brand, live status, search) + the floating dock as primary navigation. */
export default function Nav({ route, data, theme, setTheme, openPalette }: {
  route: Route; data: Data | null; theme: string; setTheme: (t: string) => void; openPalette: () => void;
}) {
  const active = route.view === "agent" ? "agents" : route.view;
  const nextTheme = theme === "" ? "light" : theme === "light" ? "dark" : "";
  const ThemeIcon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  const items: DockItem[] = [
    { title: "Overview", icon: <Home className={ic} strokeWidth={1.75} />, href: href.home, active: active === "home" },
    { title: "Control room", icon: <LayoutDashboard className={ic} strokeWidth={1.75} />, href: href.control, active: active === "control" },
    { title: "Agents", icon: <Bot className={ic} strokeWidth={1.75} />, href: href.agents, active: active === "agents" },
    { title: "Missions", icon: <Rocket className={ic} strokeWidth={1.75} />, href: href.missions, active: active === "missions" },
    { title: "Evolution", icon: <Dna className={ic} strokeWidth={1.75} />, href: href.evolutions, active: active === "evolutions" },
    { title: "Tour", icon: <Laptop className={ic} strokeWidth={1.75} />, href: href.tour, active: active === "tour" },
    { title: "Search  Ctrl K", icon: <Search className={ic} strokeWidth={1.75} />, onClick: openPalette },
    { title: `Theme: ${theme || "system"}`, icon: <ThemeIcon className={ic} strokeWidth={1.75} />, onClick: () => setTheme(nextTheme) },
    { title: "GitHub", icon: <span className={`${ic} grid place-items-center`}><GithubIcon size={20} /></span>, href: "https://github.com/Youssefghazy/Evolvra" },
  ];
  return (
    <>
      <header className="glass sticky top-0 z-40 border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <a href={href.home} aria-label="Evolvra home"><Logo size={28} /></a>
          <div className="ml-auto flex items-center gap-3">
            {data && (
              <span className="hidden items-center gap-2 text-xs text-muted sm:inline-flex" title={new Date(data.summary.generated_at).toLocaleString()}>
                <span className="pulse-dot h-1.5 w-1.5 rounded-full text-good" style={{ background: "var(--good)" }} />
                Live · updated {relTime(data.summary.generated_at)}
              </span>
            )}
            <button onClick={openPalette} className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-muted transition-colors hover:text-ink">
              <Search size={13} /> <span className="hidden sm:inline">Search</span> <Kbd>Ctrl K</Kbd>
            </button>
          </div>
        </div>
      </header>
      <div className="fixed inset-x-0 bottom-5 z-40 hidden justify-center md:flex">
        <FloatingDock items={items} />
      </div>
      <div className="fixed bottom-4 right-4 z-40 md:hidden">
        <FloatingDock items={items} />
      </div>
    </>
  );
}
