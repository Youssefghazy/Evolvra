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
          <div className="text-xs muted mb-3">{fmtDate(e.created_at)} · parent fitness {pct(e.parent_fitness)} · bank {e.bank?.length ?? "–"} tasks</div>
          <table className="w-full text-sm">
            <thead><tr><th>candidate</th><th>target</th><th>status</th><th>fitness</th><th>paired Δ</th><th>shared</th><th>notes</th></tr></thead>
            <tbody>
              {e.candidates.map((c) => {
                const best = e.winner_version != null && c.paired_delta != null && c.paired_delta === Math.max(...e.candidates.map((y) => y.paired_delta ?? -9));
                return (
                  <tr key={c.index} style={best ? { color: "var(--good)" } : undefined}>
                    <td className="mono">#{c.index}</td><td className="mono text-xs">{c.target}</td>
                    <td>{c.lint_ok ? "played" : "dropped"}</td><td className="mono">{pct(c.fitness)}</td>
                    <td className="mono">{c.paired_delta == null ? "–" : `${c.paired_delta >= 0 ? "+" : ""}${pct(c.paired_delta)}`}</td>
                    <td className="mono">{c.shared_tasks ?? "–"}</td>
                    <td className="text-xs muted">{c.lint_ok ? c.per_task.map((p) => p.critique).filter((x) => x && x !== "none").slice(0, 2).join(" · ") : c.problems.join("; ").slice(0, 160)}</td>
                  </tr>
                );
              })}
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
