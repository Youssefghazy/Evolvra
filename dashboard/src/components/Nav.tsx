import { Bot, Dna, Home, LayoutDashboard, Laptop, Moon, Rocket, Search, Sun } from "lucide-react";
import { relTime, type Data } from "../data";
import { href, type Route } from "../lib/router";
import { FloatingDock, type DockItem } from "./ui/floating-dock";
import { FloatingNav, NavAction, type NavItem } from "./ui/floating-navbar";
import { Logo, LogoMark } from "./Logo";
import { GithubIcon, Kbd } from "./ui";

const ic = "h-full w-full text-neutral-500 dark:text-neutral-300";

/** Top bar at rest, a floating pill navbar on scroll-up, and the dock for quick actions. */
export default function Nav({ route, data, theme, setTheme, openPalette }: {
  route: Route; data: Data | null; theme: "dark" | "light"; setTheme: (t: "dark" | "light") => void; openPalette: () => void;
}) {
  const active = route.view === "agent" ? "agents" : route.view;
  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  const ThemeIcon = theme === "dark" ? Moon : Sun;
  const pages = [
    { key: "home", name: "Overview", link: href.home, icon: <Home size={16} /> },
    { key: "control", name: "Control room", link: href.control, icon: <LayoutDashboard size={16} /> },
    { key: "agents", name: "Agents", link: href.agents, icon: <Bot size={16} /> },
    { key: "missions", name: "Missions", link: href.missions, icon: <Rocket size={16} /> },
    { key: "evolutions", name: "Evolution", link: href.evolutions, icon: <Dna size={16} /> },
    { key: "tour", name: "Tour", link: href.tour, icon: <Laptop size={16} /> },
  ];
  const navItems: NavItem[] = pages.map((p) => ({ name: p.name, link: p.link, icon: p.icon, active: active === p.key }));
  const dock: DockItem[] = [
    ...pages.map((p) => ({ title: p.name, href: p.link, active: active === p.key,
      icon: <span className={`${ic} grid place-items-center`}>{iconFor(p.key)}</span> })),
    { title: "Search  Ctrl K", icon: <Search className={ic} strokeWidth={1.75} />, onClick: openPalette },
    { title: theme === "dark" ? "Switch to light" : "Switch to dark", icon: <ThemeIcon className={ic} strokeWidth={1.75} />, onClick: toggle },
    { title: "GitHub", icon: <span className={`${ic} grid place-items-center`}><GithubIcon size={20} /></span>, href: "https://github.com/Youssefghazy/Evolvra" },
  ];
  return (
    <>
      <header className="relative z-30 border-b border-line">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <a href={href.home} aria-label="Evolvra home"><Logo size={28} /></a>
          <nav className="ml-6 hidden items-center gap-1 text-sm lg:flex">
            {pages.map((p) => (
              <a key={p.key} href={p.link} className={`rounded-full px-3 py-1.5 transition-colors ${active === p.key ? "bg-card-hover text-ink" : "text-muted hover:text-ink"}`}>{p.name}</a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {data && (
              <span className="hidden items-center gap-2 text-xs text-muted xl:inline-flex" title={new Date(data.summary.generated_at).toLocaleString()}>
                <span className="pulse-dot h-1.5 w-1.5 rounded-full text-good" style={{ background: "var(--good)" }} />
                Live · {relTime(data.summary.generated_at)}
              </span>
            )}
            <button onClick={toggle} aria-label={theme === "dark" ? "Switch to light" : "Switch to dark"}
              className="rounded-full border border-line bg-card p-2 text-muted transition-colors hover:text-ink"><ThemeIcon size={14} /></button>
            <button onClick={openPalette} className="inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1.5 text-xs text-muted transition-colors hover:text-ink">
              <Search size={13} /> <span className="hidden sm:inline">Search</span> <Kbd>Ctrl K</Kbd>
            </button>
          </div>
        </div>
      </header>
      <FloatingNav navItems={navItems} brand={<a href={href.home} aria-label="Evolvra home" className="text-ink"><LogoMark size={24} /></a>}
        action={<NavAction onClick={openPalette}><Search size={13} /> Search</NavAction>} />
      <div className="fixed inset-x-0 bottom-5 z-40 hidden justify-center md:flex"><FloatingDock items={dock} /></div>
      <div className="fixed bottom-4 right-4 z-40 md:hidden"><FloatingDock items={dock} /></div>
    </>
  );
}

function iconFor(key: string) {
  const p = { strokeWidth: 1.75, className: "h-full w-full" };
  switch (key) {
    case "home": return <Home {...p} />;
    case "control": return <LayoutDashboard {...p} />;
    case "agents": return <Bot {...p} />;
    case "missions": return <Rocket {...p} />;
    case "evolutions": return <Dna {...p} />;
    default: return <Laptop {...p} />;
  }
}
