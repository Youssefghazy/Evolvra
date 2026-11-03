export type Version = {
  version: number; parent: number | null; created_by: string; rationale: string | null; created_at: string;
  sha: string; content: string; fitness: number | null; tasks: number; top_failure: string | null;
};
export type Agent = {
  slug: string; name: string; division: string; emoji: string | null; color: string | null;
  current_version: number; fitness: number | null; tasks: number; versions: Version[];
};
export type Score = { metric: string; value: number; judge: string; evidence: Record<string, unknown> | null };
export type Attempt = { n: number; started_at: string; finished_at: string | null; verdict: string | null; feedback: string | null; evidence: string | null };
export type Task = {
  no: number; agent: string; task: string; acceptance: string[]; status: string; attempts: number;
  verdict: string | null; attempt_log: Attempt[]; traces: number; fitness: number | null; scores: Score[];
};
export type Mission = {
  id: string; brief: string; mode: string; status: string; summary: string | null; started_at: string;
  finished_at: string | null; tasks: Task[];
};
export type Candidate = { index: number; target: string; lint_ok: boolean; problems: string[]; fitness: number | null; per_task: { task: string; fitness: number | null; failure: string; critique: string }[] };
export type Evolution = {
  id: number; agent: string; parent_version: number; winner_version: number | null; delta: number | null;
  created_at: string; candidates: Candidate[]; diagnosis: string | null;
};
export type Summary = {
  generated_at: string; evolvra_version: string; agents: number; versions: number; missions: number; tasks: number;
  evolutions: number; promotions: number; providers: { provider: string; requests: number; tokens: number }[];
};
export type Data = { agents: Agent[]; missions: Mission[]; evolutions: Evolution[]; summary: Summary };

const DIVISION_COLORS: Record<string, string> = {
  engineering: "#3B82F6", design: "#EC4899", marketing: "#F97316", product: "#D946EF", testing: "#10B981",
  security: "#EF4444", sales: "#10B981", finance: "#22C55E", research: "#7C3AED", support: "#0EA5E9",
};
export const divisionColor = (d: string) => DIVISION_COLORS[d] ?? "#6366F1";

async function getJson<T>(name: string): Promise<T> {
  const res = await fetch(`${import.meta.env.BASE_URL}data/${name}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}

export async function loadData(): Promise<Data> {
  const [agents, missions, evolutions, summary] = await Promise.all([
    getJson<Agent[]>("agents.json"), getJson<Mission[]>("missions.json"),
    getJson<Evolution[]>("evolutions.json"), getJson<Summary>("summary.json"),
  ]);
  return { agents, missions, evolutions, summary };
}

export const pct = (v: number | null | undefined) => (v == null ? "–" : `${Math.round(v * 100)}%`);
export const fmtDate = (s: string | null | undefined) => (s ? new Date(s).toLocaleString() : "–");
export const fitnessColor = (v: number | null | undefined) =>
  v == null ? "var(--muted)" : v >= 0.75 ? "var(--good)" : v >= 0.5 ? "var(--warn)" : "var(--bad)";
