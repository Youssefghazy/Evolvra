import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { loadData, type Data } from "./data";
import { useRoute } from "./lib/router";
import { Backdrop } from "./components/fx";
import Nav from "./components/Nav";
import { LogoMark } from "./components/Logo";
import CommandPalette from "./components/CommandPalette";
import { Empty } from "./components/ui";
import Home from "./pages/Home";
import Agents from "./pages/Agents";
import AgentDetail from "./pages/AgentDetail";
import Missions from "./pages/Missions";
import Evolutions from "./pages/Evolutions";
import Control from "./pages/Control";
import Tour from "./pages/Tour";

export default function App() {
  const route = useRoute();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [palette, setPalette] = useState(false);
  const [theme, setTheme] = useState<string>(() => { try { return localStorage.getItem("theme") || ""; } catch { return ""; } });

  useEffect(() => { loadData().then(setData).catch((e) => setError(String(e))); }, []);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme; else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("theme", theme); } catch { /* private mode */ }
  }, [theme]);
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setPalette((p) => !p); }
      if (e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) { e.preventDefault(); setPalette(true); }
    };
    addEventListener("keydown", on);
    return () => removeEventListener("keydown", on);
  }, []);

  let page: React.ReactNode;
  if (error) page = <Empty title="Could not load the data" hint={`${error}. Run \`evolvra export\` and push.`} />;
  else if (!data) page = <Loading />;
  else if (route.view === "agents") page = <Agents data={data} />;
  else if (route.view === "agent") page = <AgentDetail data={data} slug={route.id ?? ""} />;
  else if (route.view === "missions") page = <Missions data={data} id={route.id} />;
  else if (route.view === "evolutions") page = <Evolutions data={data} />;
  else if (route.view === "control") page = <Control data={data} />;
  else if (route.view === "tour") page = <Tour data={data} />;
  else page = <Home data={data} />;

  return (
    <div className="relative min-h-screen">
      <Backdrop />
      <Nav route={route} data={data} theme={theme} setTheme={setTheme} openPalette={() => setPalette(true)} />
      <main className="mx-auto max-w-6xl px-4 pb-36 pt-8 md:pt-10">
        <AnimatePresence mode="wait">
          <motion.div key={`${route.view}/${route.id ?? ""}`}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}>
            {page}
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 pb-28 pt-8 text-xs text-muted md:flex-row md:items-center md:justify-between">
          <span className="inline-flex items-center gap-2"><LogoMark size={16} /> Evolvra · every number on this site came from free-tier models and a $0 budget.</span>
          <span>Personas from msitarzewski/agency-agents (MIT) · ideas from GEPA, OpenEvolve, Darwin Gödel Machine</span>
        </div>
      </footer>
      <CommandPalette open={palette} onClose={() => setPalette(false)} data={data} />
    </div>
  );
}

function Loading() {
  return (
    <div className="space-y-4">
      <div className="skeleton h-12 w-2/3" /><div className="skeleton h-6 w-1/2" />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-20" />)}</div>
      <div className="skeleton h-64" />
    </div>
  );
}
