import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { type Data, divisionColor, fmtDate, pct } from "../data";
import { Badge, Card, Fitness } from "./ui";
import Diff from "./Diff";
import { Empty } from "../App";

export default function AgentPage({ data, slug }: { data: Data; slug: string }) {
  const agent = data.agents.find((a) => a.slug === slug);
  const [pair, setPair] = useState<[number, number] | null>(null);
  const [showPersona, setShowPersona] = useState(false);
  if (!agent) return <Empty title="Unknown agent" hint={slug} />;
  const vs = agent.versions;
  const [va, vb] = pair ?? [Math.max(1, vs.length - 1), vs.length];
  const A = vs.find((v) => v.version === va), B = vs.find((v) => v.version === vb);
  const chart = vs.map((v) => ({ name: `v${v.version}`, fitness: v.fitness == null ? null : Math.round(v.fitness * 100) }));
  const evos = data.evolutions.filter((e) => e.agent === slug);
  const missions = data.missions.flatMap((m) => m.tasks.filter((t) => t.agent === slug).map((t) => ({ m, t })));

  return (
    <div className="grid gap-4">
      <div className="panel p-5" style={{ borderTop: `3px solid ${divisionColor(agent.division)}` }}>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{agent.emoji} {agent.name}</h1>
          <Badge color={divisionColor(agent.division)}>{agent.division}</Badge>
          <span className="chip mono">v{agent.current_version}</span>
          <span className="ml-auto"><Fitness value={agent.fitness} width={140} /></span>
        </div>
        <div className="text-xs muted mt-2">{agent.tasks} tasks scored · {vs.length} version(s) · {evos.length} evolution run(s)</div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card title="Genealogy">
          <ol className="relative border-l pl-5 grid gap-4" style={{ borderColor: "var(--line)" }}>
            {vs.map((v) => (
              <li key={v.version} className="relative">
                <span className="absolute -left-[27px] top-1 h-3 w-3 rounded-full" style={{ background: v.version === agent.current_version ? "var(--accent)" : "var(--line)" }} />
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium mono">v{v.version}</span>
                  <span className="chip">{v.created_by}</span>
                  {v.parent && <span className="muted text-xs">← v{v.parent}</span>}
                  <span className="ml-auto"><Fitness value={v.fitness} width={70} /></span>
                </div>
                <div className="text-xs muted mt-1">{fmtDate(v.created_at)} · {v.sha}</div>
                {v.rationale && <div className="text-xs mt-1">{v.rationale}</div>}
                {v.parent && <button className="text-xs mt-1" style={{ color: "var(--accent)" }} onClick={() => setPair([v.parent!, v.version])}>show diff v{v.parent} → v{v.version}</button>}
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Fitness by version">
          {chart.every((c) => c.fitness == null) ? <div className="muted text-sm">Not scored yet.</div> : (
            <div style={{ height: 220 }}>
              <ResponsiveContainer>
                <LineChart data={chart} margin={{ left: -20, right: 12 }}>
                  <CartesianGrid stroke="var(--line)" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: "var(--muted)", fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "var(--panel)", border: "1px solid var(--line)", borderRadius: 10, color: "var(--text)" }} formatter={(v) => [`${v}%`, "fitness"]} />
                  <Line type="monotone" dataKey="fitness" stroke="var(--accent)" strokeWidth={2} dot={{ r: 4 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {evos.length > 0 && (
            <ul className="mt-3 grid gap-1 text-xs">
              {evos.map((e) => (
                <li key={e.id} className="flex justify-between"><span>gen v{e.parent_version}: {e.candidates.length} candidates</span>
                  <span className="mono" style={{ color: e.winner_version ? "var(--good)" : "var(--muted)" }}>{e.winner_version ? `promoted v${e.winner_version} (+${pct(e.delta)})` : "no winner"}</span></li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title={vs.length > 1 ? `Diff v${va} → v${vb}` : "Persona"} right={
        <div className="flex gap-2 text-xs">
          {vs.length > 1 && (
            <>
              <select className="chip" value={va} onChange={(e) => setPair([Number(e.target.value), vb])}>{vs.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}</select>
              <span className="muted">→</span>
              <select className="chip" value={vb} onChange={(e) => setPair([va, Number(e.target.value)])}>{vs.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}</select>
            </>
          )}
          <button className="chip" onClick={() => setShowPersona(!showPersona)}>{showPersona ? "hide persona" : "show persona"}</button>
        </div>
      }>
        {vs.length > 1 && A && B ? <Diff a={A.content} b={B.content} labelA={`v${A.version}`} labelB={`v${B.version}`} /> : <div className="muted text-sm">Only one version so far. Evolve it to see a diff here.</div>}
        {showPersona && B && <pre className="mono text-xs mt-3 overflow-auto rounded-lg p-3 whitespace-pre-wrap" style={{ background: "var(--panel-2)", maxHeight: 520 }}>{B.content}</pre>}
      </Card>

      <Card title="Tasks">
        {missions.length === 0 ? <div className="muted text-sm">No tasks yet.</div> : (
          <table className="w-full text-sm">
            <thead><tr><th>mission</th><th>task</th><th>attempts</th><th>verdict</th><th>fitness</th></tr></thead>
            <tbody>
              {missions.map(({ m, t }) => (
                <tr key={`${m.id}-${t.no}`}>
                  <td><a href={`#/missions/${encodeURIComponent(m.id)}`} className="text-xs muted">{m.brief.slice(0, 50)}</a></td>
                  <td>{t.task}</td><td>{t.attempts}</td><td>{t.verdict ?? "–"}</td><td><Fitness value={t.fitness} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
