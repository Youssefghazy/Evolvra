import { useEffect, useMemo, useState } from "react";
import { loadData, type Data } from "./data";
import Overview from "./components/Overview";
import Roster from "./components/Roster";
import AgentPage from "./components/AgentPage";
import Missions from "./components/Missions";
import Evolutions from "./components/Evolutions";

type Route = { view: string; id?: string };
const parse = (hash: string): Route => {
  const [view = "overview", id] = hash.replace(/^#\/?/, "").split("/");
  return { view: view || "overview", id: id ? decodeURIComponent(id) : undefined };
};

const NAV = [["overview", "Overview"], ["roster", "Roster"], ["missions", "Missions"], ["evolutions", "Evolutions"]];

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [route, setRoute] = useState<Route>(() => parse(location.hash));
  const [theme, setTheme] = useState<string>(() => { try { return localStorage.getItem("theme") || ""; } catch { return ""; } });

  useEffect(() => { loadData().then(setData).catch((e) => setError(String(e))); }, []);
  useEffect(() => {
    const on = () => setRoute(parse(location.hash));
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme; else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("theme", theme); } catch { /* private mode */ }
  }, [theme]);

  const body = useMemo(() => {
    if (error) return <Empty title="Could not load data" hint={`${error}. Run \`evolvra export\` and redeploy.`} />;
    if (!data) return <div className="muted p-10 text-center">Loading…</div>;
    switch (route.view) {
      case "roster": return <Roster data={data} />;
      case "agent": return <AgentPage data={data} slug={route.id ?? ""} />;
      case "missions": return <Missions data={data} id={route.id} />;
      case "evolutions": return <Evolutions data={data} />;
      default: return <Overview data={data} />;
    }
  }, [data, error, route]);

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-10 backdrop-blur border-b" style={{ borderColor: "var(--line)", background: "color-mix(in srgb, var(--bg) 85%, transparent)" }}>
        <div className="mx-auto max-w-6xl px-4 py-3 flex items-center gap-3 flex-wrap">
          <a href="#/" className="flex items-center gap-2 font-semibold text-lg mr-2">
            <span>🧬</span><span>Evolvra</span>
            <span className="chip muted hidden sm:inline-flex">survival of the promptest</span>
          </a>
          <nav className="flex gap-1 text-sm">
            {NAV.map(([k, label]) => (
              <a key={k} href={`#/${k}`} className={`navlink ${route.view === k || (k === "roster" && route.view === "agent") ? "active" : ""}`}>{label}</a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 text-xs muted">
            {data && <span className="hidden md:inline">updated {new Date(data.summary.generated_at).toLocaleString()}</span>}
            <button className="chip" onClick={() => setTheme(theme === "light" ? "dark" : theme === "dark" ? "" : "light")} title="Theme">
              {theme === "light" ? "☀️ light" : theme === "dark" ? "🌙 dark" : "🖥️ auto"}
            </button>
            <a className="chip" href="https://github.com/Youssefghazy/Evolvra" target="_blank" rel="noreferrer">GitHub ↗</a>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{body}</main>
      <footer className="mx-auto max-w-6xl px-4 py-8 text-xs muted">
        Built with zero paid services. Personas from msitarzewski/agency-agents (MIT). Evolution ideas from GEPA, OpenEvolve and the Darwin Gödel Machine.
      </footer>
    </div>
  );
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="panel p-10 text-center">
      <div className="text-lg font-medium">{title}</div>
      <div className="muted mt-2 text-sm">{hint}</div>
    </div>
  );
}
