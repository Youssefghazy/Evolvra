import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight, Bot, CornerDownLeft, Dna, Laptop, LayoutDashboard, Rocket, Search } from "lucide-react";
import { type Data } from "../data";
import { href } from "../lib/router";
import { Kbd } from "./ui";

type Item = { id: string; label: string; hint: string; to: string; group: string; icon: React.ReactNode };

export default function CommandPalette({ open, onClose, data }: { open: boolean; onClose: () => void; data: Data | null }) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  const items = useMemo<Item[]>(() => {
    const pages: Item[] = [
      { id: "p-home", label: "Overview", hint: "Live status and the latest promotion", to: href.home, group: "Pages", icon: <LayoutDashboard size={15} /> },
      { id: "p-agents", label: "Agents", hint: "The roster and their fitness", to: href.agents, group: "Pages", icon: <Bot size={15} /> },
      { id: "p-missions", label: "Missions", hint: "Every task, attempt and verdict", to: href.missions, group: "Pages", icon: <Rocket size={15} /> },
      { id: "p-evo", label: "Evolution", hint: "Every generation, promoted or refused", to: href.evolutions, group: "Pages", icon: <Dna size={15} /> },
      { id: "p-control", label: "Control room", hint: "KPIs, quality over time, judges, activity", to: href.control, group: "Pages", icon: <LayoutDashboard size={15} /> },
      { id: "p-tour", label: "Tour", hint: "Watch a real mission replay on a laptop", to: href.tour, group: "Pages", icon: <Laptop size={15} /> },
    ];
    if (!data) return pages;
    const agents = data.agents.map<Item>((a) => ({
      id: `a-${a.slug}`, label: a.name, hint: `${a.division} · v${a.current_version}`,
      to: href.agent(a.slug), group: "Agents", icon: <Bot size={15} />,
    }));
    const missions = data.missions.map<Item>((m) => ({
      id: `m-${m.id}`, label: m.brief, hint: `${m.mode} · ${m.tasks.length} tasks`, to: href.mission(m.id), group: "Missions", icon: <Rocket size={15} />,
    }));
    return [...pages, ...agents, ...missions];
  }, [data]);

  const filtered = useMemo(() => {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    return items.filter((i) => terms.every((t) => `${i.label} ${i.hint} ${i.group}`.toLowerCase().includes(t))).slice(0, 12);
  }, [items, q]);

  useEffect(() => { if (open) { setQ(""); setSel(0); setTimeout(() => input.current?.focus(), 20); } }, [open]);
  useEffect(() => { setSel(0); }, [q]);

  const go = (i: Item | undefined) => { if (!i) return; location.hash = i.to.slice(1); onClose(); };
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(filtered.length - 1, s + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
    if (e.key === "Enter") { e.preventDefault(); go(filtered[sel]); }
    if (e.key === "Escape") onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-50 grid items-start justify-center bg-black/50 px-4 pt-[12vh] backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.div role="dialog" aria-label="Search" onClick={(e) => e.stopPropagation()} onKeyDown={onKey}
            className="w-full max-w-xl overflow-hidden rounded-2xl border border-line-strong bg-card-solid shadow-2xl"
            initial={{ opacity: 0, y: -12, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}>
            <div className="flex items-center gap-3 border-b border-line px-4 py-3">
              <Search size={16} className="text-muted" />
              <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Jump to an agent, mission or page…"
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted" />
              <Kbd>Esc</Kbd>
            </div>
            <ul className="max-h-[50vh] overflow-y-auto p-2">
              {filtered.length === 0 && <li className="px-3 py-8 text-center text-sm text-muted">No matches.</li>}
              {filtered.map((i, idx) => (
                <li key={i.id}>
                  <button onMouseEnter={() => setSel(idx)} onClick={() => go(i)}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm ${idx === sel ? "bg-card-hover text-ink" : "text-ink2"}`}>
                    <span className="text-muted">{i.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate">{i.label}</span>
                      <span className="block truncate text-xs text-muted">{i.group} · {i.hint}</span>
                    </span>
                    {idx === sel ? <CornerDownLeft size={14} className="text-muted" /> : <ArrowRight size={14} className="opacity-0" />}
                  </button>
                </li>
              ))}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
