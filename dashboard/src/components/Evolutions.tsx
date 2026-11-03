import { useState } from "react";
import { type Data, fmtDate, pct } from "../data";
import { Card } from "./ui";
import { Empty } from "../App";

export default function Evolutions({ data }: { data: Data }) {
  const [open, setOpen] = useState<number | null>(null);
  if (data.evolutions.length === 0) return <Empty title="No evolution runs yet" hint="Run `evolvra evolve <agent>` after scoring a few missions, then `evolvra export`." />;
  return (
    <div className="grid gap-4">
      {[...data.evolutions].reverse().map((e) => (
        <Card key={e.id} title={<span><a href={`#/agent/${e.agent}`} style={{ color: "var(--text)" }}>{e.agent}</a> · generation from v{e.parent_version}</span>}
              right={<span className="chip" style={{ color: e.winner_version ? "var(--good)" : "var(--muted)" }}>{e.winner_version ? `promoted v${e.winner_version} (+${pct(e.delta)})` : `no winner (${e.delta == null ? "–" : pct(e.delta)})`}</span>}>
          <div className="text-xs muted mb-3">{fmtDate(e.created_at)}</div>
          <table className="w-full text-sm">
            <thead><tr><th>candidate</th><th>target</th><th>lint</th><th>fitness</th><th>notes</th></tr></thead>
            <tbody>
              {e.candidates.map((c) => (
                <tr key={c.index} style={c.index === (e.winner_version ? e.candidates.find((x) => x.fitness != null && x.fitness === Math.max(...e.candidates.map((y) => y.fitness ?? -1)))?.index : -1) ? { color: "var(--good)" } : undefined}>
                  <td className="mono">#{c.index}</td><td className="mono text-xs">{c.target}</td>
                  <td>{c.lint_ok ? "ok" : "failed"}</td><td className="mono">{pct(c.fitness)}</td>
                  <td className="text-xs muted">{c.lint_ok ? c.per_task.map((p) => p.critique).filter((x) => x && x !== "none").slice(0, 2).join(" · ") : c.problems.join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {e.diagnosis && (
            <div className="mt-3">
              <button className="chip" onClick={() => setOpen(open === e.id ? null : e.id)}>{open === e.id ? "hide diagnosis" : "show diagnosis"}</button>
              {open === e.id && <pre className="mono text-xs mt-2 overflow-auto rounded-lg p-3 whitespace-pre-wrap" style={{ background: "var(--panel-2)", maxHeight: 420 }}>{e.diagnosis}</pre>}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
