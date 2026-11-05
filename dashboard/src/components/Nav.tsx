import { useState } from "react";
import { Bot, Dna, Home, LayoutDashboard, Laptop, Menu, Moon, Rocket, Search, Sun } from "lucide-react";
import { MobileMenu, MobileTabBar } from "./MobileNav";
import { relTime, type Data } from "../data";
import { href, type Route } from "../lib/router";
import { FloatingDock, type DockItem } from "./ui/floating-dock";
import { FloatingNav, NavAction, type NavItem } from "./ui/floating-navbar";
import { NavLinks } from "./ui/nav-links";
import { cn } from "../lib/utils";
import { Logo, LogoMark } from "./Logo";
import { GithubIcon, Kbd } from "./ui";

const ic = "h-full w-full text-neutral-500 dark:text-neutral-300";

/** Top bar at rest, a floating pill navbar on scroll-up, and the dock for quick actions. */
export default function Nav({ route, data, theme, setTheme, openPalette }: {
  route: Route; data: Data | null; theme: "dark" | "light"; setTheme: (t: "dark" | "light") => void; openPalette: () => void;
}) {
  const active = route.view === "agent" ? "agents" : route.view;
  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  const [menu, setMenu] = useState(false);
  const ThemeIcon = theme === "dark" ? Moon : Sun;
  const pages = [
    { key: "home", name: "Overview", link: href.home, icon: <Home size={16} /> },
    { key: "control", name: "Control room", link: href.control, icon: <LayoutDashboard size={16} /> },
    { key: "agents", name: "Agents", link: href.agents, icon: <Bot size={16} /> },
    { key: "missions", name: "Missions", link: href.missions, icon: <Rocket size={16} /> },
    { key: "evolutions", name: "Evolution", link: href.evolutions, icon: <Dna size={16} /> },
    { key: "tour", name: "Tour", link: href.tour, icon: <Laptop size={16} /> },
  ];
  const navItems: NavItem[] = pages.map((p) => ({ key: p.key, name: p.name, link: p.link, icon: p.icon, active: active === p.key }));
  const btn = "inline-flex items-center gap-2 rounded-full border border-line bg-card text-muted transition-[color,background-color,border-color,box-shadow] duration-200 hover:border-line-strong hover:bg-card-hover hover:text-ink hover:shadow-[0_0_0_1px_var(--glow),0_6px_20px_-8px_var(--glow)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent";
  const dock: DockItem[] = [
    ...pages.map((p) => ({ title: p.name, href: p.link, active: active === p.key,
      icon: <span className={`${ic} grid place-items-center`}>{iconFor(p.key)}</span> })),
    { title: "Search  Ctrl K", icon: <Search className={ic} strokeWidth={1.75} />, onClick: openPalette },
    { title: theme === "dark" ? "Switch to light" : "Switch to dark", icon: <ThemeIcon className={ic} strokeWidth={1.75} />, onClick: toggle },
    { title: "GitHub", icon: <span className={`${ic} grid place-items-center`}><GithubIcon size={20} /></span>, href: "https://github.com/Youssefghazy/Evolvra" },
  ];
  return (
    <>
      <header className="relative z-30 border-b border-line bg-card-solid/40 backdrop-blur-md">
        <span aria-hidden className="pointer-events-none absolute inset-x-0 -bottom-px mx-auto h-px max-w-3xl"
          style={{ background: "linear-gradient(90deg, transparent, var(--accent), var(--accent-2), transparent)", opacity: 0.55 }} />
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 md:gap-3 md:py-3">
          <a href={href.home} aria-label="Evolvra home" className="rounded-lg outline-none transition-opacity hover:opacity-80 focus-visible:ring-2 focus-visible:ring-accent"><Logo size={28} /></a>
          <NavLinks id="header" className="ml-6 hidden gap-0.5 lg:flex"
            items={pages.map((p) => ({ key: p.key, name: p.name, link: p.link, active: active === p.key,
              icon: <span className="hidden xl:grid [&>svg]:h-3.5 [&>svg]:w-3.5">{p.icon}</span> }))} />
          <div className="ml-auto flex items-center gap-3">
            {data && (
              <span className="hidden items-center gap-2 text-xs text-muted xl:inline-flex" title={new Date(data.summary.generated_at).toLocaleString()}>
                <span className="pulse-dot h-1.5 w-1.5 rounded-full text-good" style={{ background: "var(--good)" }} />
                Live · {relTime(data.summary.generated_at)}
              </span>
            )}
            <button onClick={toggle} aria-label={theme === "dark" ? "Switch to light" : "Switch to dark"}
              className={cn(btn, "hidden p-2 md:inline-flex [&>svg]:transition-transform [&>svg]:duration-500 hover:[&>svg]:rotate-[24deg]")}><ThemeIcon size={14} /></button>
            <button onClick={openPalette} className={cn(btn, "hidden px-3 py-1.5 text-xs md:inline-flex")}>
              <Search size={13} /> Search <Kbd>Ctrl K</Kbd>
            </button>
            {/* phone: two 40 px icon buttons; everything else lives in the tab bar and the menu sheet */}
            <button onClick={openPalette} aria-label="Search" className={cn(btn, "h-10 w-10 justify-center md:hidden")}><Search size={17} /></button>
            <button onClick={() => setMenu(true)} aria-label="Open menu" aria-expanded={menu} className={cn(btn, "h-10 w-10 justify-center md:hidden")}><Menu size={18} /></button>
          </div>
        </div>
      </header>
      <FloatingNav className="hidden md:flex" navItems={navItems} brand={<a href={href.home} aria-label="Evolvra home" className="text-ink"><LogoMark size={24} /></a>}
        action={<NavAction onClick={openPalette}><Search size={13} /> Search</NavAction>} />
      <div className="fixed inset-x-0 bottom-5 z-40 hidden justify-center md:flex"><FloatingDock items={dock} /></div>
      <MobileTabBar active={active} />
      <MobileMenu open={menu} onClose={() => setMenu(false)} active={active} theme={theme} toggleTheme={toggle} openPalette={openPalette} />
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
