import { type Data, type Mission, fmtDate, pct } from "../data";
import { Card, Fitness, Verdict } from "./ui";
import { Empty } from "../App";

export default function Missions({ data, id }: { data: Data; id?: string }) {
  if (id) {
    const m = data.missions.find((x) => x.id === id);
    return m ? <MissionDetail m={m} /> : <Empty title="Unknown mission" hint={id} />;
  }
  if (data.missions.length === 0) return <Empty title="No missions yet" hint="Run /evolvra:mission in Claude Code, then `evolvra ingest` and `evolvra export`." />;
  return (
    <Card title={`${data.missions.length} missions`}>
      <table className="w-full text-sm">
        <thead><tr><th>brief</th><th>mode</th><th>tasks</th><th>attempts</th><th>status</th><th>started</th></tr></thead>
        <tbody>
          {data.missions.map((m) => (
            <tr key={m.id}>
              <td><a href={`#/missions/${encodeURIComponent(m.id)}`}>{m.brief}</a><div className="text-xs muted mono">{m.id}</div></td>
              <td>{m.mode}</td>
              <td>{m.tasks.filter((t) => t.status === "done").length}/{m.tasks.length}</td>
              <td>{m.tasks.reduce((n, t) => n + t.attempts, 0)}</td>
              <td><Verdict v={m.status.toUpperCase()} /></td>
              <td className="text-xs muted">{fmtDate(m.started_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function MissionDetail({ m }: { m: Mission }) {
  return (
    <div className="grid gap-4">
      <div className="panel p-5">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-xl font-semibold">{m.brief}</h1>
          <span className="chip">{m.mode}</span><Verdict v={m.status.toUpperCase()} />
        </div>
        <div className="text-xs muted mt-2 mono">{m.id} · {fmtDate(m.started_at)} → {fmtDate(m.finished_at)}</div>
        {m.summary && <p className="text-sm mt-3">{m.summary}</p>}
      </div>
      {m.tasks.map((t) => {
        const ensemble = t.scores.filter((s) => s.judge === "ensemble");
        const judges = [...new Set(t.scores.filter((s) => !["ensemble", "deterministic"].includes(s.judge)).map((s) => s.judge))];
        const det = t.scores.filter((s) => s.judge === "deterministic");
        const critique = (ensemble[0]?.evidence as { critique?: string; failure_class?: string } | null);
        return (
          <Card key={t.no} title={`#${t.no} · ${t.agent}`} right={<span className="flex items-center gap-3"><Verdict v={t.verdict} /><Fitness value={t.fitness} /></span>}>
            <div className="text-sm">{t.task}</div>
            {t.acceptance.length > 0 && <ul className="mt-2 text-xs muted list-disc pl-5">{t.acceptance.map((a, i) => <li key={i}>{a}</li>)}</ul>}
            <div className="mt-3 grid md:grid-cols-2 gap-3">
              <div>
                <div className="text-xs muted uppercase tracking-wide mb-1">Attempts ({t.attempts}) · {t.traces} traces</div>
                <ol className="grid gap-1 text-xs">
                  {t.attempt_log.map((a) => (
                    <li key={a.n} className="flex gap-2"><span className="mono">#{a.n}</span><Verdict v={a.verdict} />
                      <span>{a.evidence ?? a.feedback ?? ""}</span></li>
                  ))}
                </ol>
              </div>
              <div>
                <div className="text-xs muted uppercase tracking-wide mb-1">Scores</div>
                {t.scores.length === 0 ? <div className="text-xs muted">Not scored yet.</div> : (
                  <table className="text-xs w-full">
                    <thead><tr><th>metric</th><th>ensemble</th>{judges.map((j) => <th key={j} title={j}>{j.split("/").pop()}</th>)}</tr></thead>
                    <tbody>
                      {["rubric:correctness", "rubric:completeness", "rubric:quality", "rubric:evidence"].filter((mt) => ensemble.some((s) => s.metric === mt)).map((mt) => (
                        <tr key={mt}><td>{mt.replace("rubric:", "")}</td><td className="mono">{pct(ensemble.find((s) => s.metric === mt)?.value)}</td>
                          {judges.map((j) => <td key={j} className="mono muted">{pct(t.scores.find((s) => s.judge === j && s.metric === mt)?.value)}</td>)}</tr>
                      ))}
                      {det.map((s) => <tr key={s.metric}><td className="muted">{s.metric}</td><td className="mono" colSpan={judges.length + 1}>{pct(s.value)}</td></tr>)}
                    </tbody>
                  </table>
                )}
                {critique?.critique && <div className="text-xs mt-2"><span className="muted">critique:</span> {critique.critique} {critique.failure_class && critique.failure_class !== "none" && <span className="chip ml-1">{critique.failure_class}</span>}</div>}
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
