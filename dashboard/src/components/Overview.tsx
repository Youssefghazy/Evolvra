import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { type Data, divisionColor, fmtDate, pct } from "../data";
import { Card, Fitness, Stat, Verdict } from "./ui";
import Story from "./Story";
import { Empty } from "../App";

export default function Overview({ data }: { data: Data }) {
  const s = data.summary;
  const chart = data.agents.filter((a) => a.fitness != null).map((a) => ({ name: a.slug, fitness: Math.round((a.fitness ?? 0) * 100), fill: divisionColor(a.division) }));
  const calls = s.providers.reduce((n, p) => n + (p.requests || 0), 0);
  return (
    <div className="grid gap-4">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Agents" value={s.agents} sub={`${s.versions} versions`} />
        <Stat label="Missions" value={s.missions} sub={`${s.tasks} tasks`} />
        <Stat label="Evolutions" value={s.evolutions} sub={`${s.promotions} promoted`} />
        <Stat label="Free-tier calls" value={calls} sub={s.providers.map((p) => `${p.provider} ${p.requests}`).join(" · ") || "none yet"} />
        <Stat label="Total spend" value="$0.00" sub="by design" />
      </div>

      <Story data={data} />

      <Card title="Current fitness by agent">
        {chart.length === 0 ? (
          <Empty title="No scored tasks yet" hint="Run a mission, then `evolvra ingest`, `evolvra score`, `evolvra export`." />
        ) : (
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ left: -20, right: 8 }}>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} interval={0} angle={-20} height={50} textAnchor="end" />
                <YAxis domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)" }} formatter={(v) => [`${v}%`, "fitness"]} />
                <Bar dataKey="fitness" radius={[6, 6, 0, 0]} maxBarSize={56} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Recent missions" right={<a className="text-xs muted" href="#/missions">all →</a>}>
          {data.missions.length === 0 ? <div className="muted text-sm">None yet.</div> : (
            <ul className="grid gap-2">
              {data.missions.slice(0, 5).map((m) => (
                <li key={m.id}>
                  <a href={`#/missions/${encodeURIComponent(m.id)}`} className="flex items-start justify-between gap-3 hover:opacity-80">
                    <div>
                      <div className="text-sm">{m.brief}</div>
                      <div className="text-xs muted">{m.mode} · {m.tasks.length} tasks · {fmtDate(m.started_at)}</div>
                    </div>
                    <Verdict v={m.status.toUpperCase()} />
                  </a>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Recent evolutions" right={<a className="text-xs muted" href="#/evolutions">all →</a>}>
          {data.evolutions.length === 0 ? <div className="muted text-sm">No generations yet. Run `evolvra evolve &lt;agent&gt;`.</div> : (
            <ul className="grid gap-2">
              {[...data.evolutions].reverse().slice(0, 5).map((e) => (
                <li key={e.id} className="flex items-center justify-between gap-3 text-sm">
                  <a href={`#/agent/${e.agent}`} className="hover:opacity-80">
                    <span className="font-medium">{e.agent}</span> <span className="muted">v{e.parent_version} → {e.winner_version ? `v${e.winner_version}` : "no winner"}</span>
                  </a>
                  <span className="mono text-xs" style={{ color: e.winner_version ? "var(--good)" : "var(--muted)" }}>{e.delta == null ? "–" : `${e.delta >= 0 ? "+" : ""}${pct(e.delta)}`}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Weakest agents (evolution queue)">
        <table className="w-full text-sm">
          <thead><tr><th>agent</th><th>division</th><th>version</th><th>tasks</th><th>fitness</th><th>top failure</th></tr></thead>
          <tbody>
            {[...data.agents].sort((a, b) => (a.fitness ?? 2) - (b.fitness ?? 2)).slice(0, 6).map((a) => {
              const cur = a.versions.find((v) => v.version === a.current_version);
              return (
                <tr key={a.slug}>
                  <td><a href={`#/agent/${a.slug}`}>{a.emoji} {a.name}</a></td>
                  <td><span className="chip" style={{ color: divisionColor(a.division) }}>{a.division}</span></td>
                  <td className="mono">v{a.current_version}</td>
                  <td>{a.tasks}</td>
                  <td><Fitness value={a.fitness} /></td>
                  <td className="mono text-xs muted">{cur?.top_failure ?? "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
