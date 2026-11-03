import { type Data, divisionColor, pct } from "../data";
import { Card } from "./ui";

/** The headline a visitor should see first: the latest promotion, with arena and real-mission numbers. */
export default function Story({ data }: { data: Data }) {
  const promo = [...data.evolutions].reverse().find((e) => e.winner_version != null);
  if (!promo) return null;
  const agent = data.agents.find((a) => a.slug === promo.agent);
  if (!agent) return null;
  const parent = agent.versions.find((v) => v.version === promo.parent_version);
  const winner = agent.versions.find((v) => v.version === promo.winner_version);
  const cand = promo.candidates.find((c) => c.lint_ok && c.paired_delta != null && c.paired_delta === promo.delta);
  const arenaParent = promo.parent_fitness ?? null;
  const arenaWinner = cand?.fitness ?? null;
  const realParent = parent?.fitness ?? null;
  const realWinner = winner?.fitness ?? null;
  const verdict = realWinner == null ? "awaiting real missions"
    : realParent != null && realWinner >= realParent ? "holding up on real missions" : "not yet better on real missions";
  return (
    <Card title="Latest promotion" right={<a className="text-xs" style={{ color: "var(--accent)" }} href={`#/agent/${agent.slug}`}>see the diff →</a>}>
      <div className="grid md:grid-cols-[1.2fr_1fr_1fr] gap-4 items-center">
        <div>
          <div className="text-2xl font-semibold">{agent.emoji} {agent.name}</div>
          <div className="text-sm mt-1"><span className="chip mono">v{promo.parent_version}</span> <span className="muted">→</span> <span className="chip mono" style={{ borderColor: divisionColor(agent.division), color: divisionColor(agent.division) }}>v{promo.winner_version}</span></div>
          <p className="text-sm muted mt-3">{winner?.rationale ?? cand?.target ?? ""}</p>
          <div className="text-xs mt-2 chip" style={{ color: realWinner != null && realParent != null && realWinner >= realParent ? "var(--good)" : "var(--warn)" }}>{verdict}</div>
        </div>
        <Metric label="Arena (held-out tasks)" a={arenaParent} b={arenaWinner} sub={`${cand?.shared_tasks ?? promo.bank?.length ?? "–"} shared tasks · paired Δ ${promo.delta == null ? "–" : (promo.delta >= 0 ? "+" : "") + pct(promo.delta)}`} />
        <Metric label="Real missions" a={realParent} b={realWinner} sub={`${parent?.tasks ?? 0} tasks on v${promo.parent_version} · ${winner?.tasks ?? 0} on v${promo.winner_version}`} />
      </div>
    </Card>
  );
}

function Metric({ label, a, b, sub }: { label: string; a: number | null; b: number | null; sub: string }) {
  const up = a != null && b != null && b >= a;
  return (
    <div className="panel p-4" style={{ background: "var(--panel-2)" }}>
      <div className="text-xs muted uppercase tracking-wide">{label}</div>
      <div className="flex items-baseline gap-2 mt-2">
        <span className="mono text-lg muted">{pct(a)}</span>
        <span className="muted">→</span>
        <span className="mono text-3xl font-semibold" style={{ color: b == null ? "var(--muted)" : up ? "var(--good)" : "var(--bad)" }}>{pct(b)}</span>
      </div>
      <div className="text-xs muted mt-1">{sub}</div>
    </div>
  );
}
