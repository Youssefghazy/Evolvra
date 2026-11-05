import { diffLines } from "diff";

export type Version = {
  version: number; parent: number | null; created_by: string; rationale: string | null; created_at: string;
  sha: string; content: string; fitness: number | null; tasks: number; top_failure: string | null;
};
export type Agent = {
  slug: string; name: string; division: string; emoji: string | null; color: string | null;
  current_version: number; fitness: number | null; tasks: number; versions: Version[];
};
export type Score = { metric: string; value: number; judge: string; evidence: Record<string, unknown> | null };
export type Attempt = {
  n: number; started_at: string; finished_at: string | null; verdict: string | null; feedback: string | null;
  evidence: string | null; reopened_by_qa?: boolean; caused_by_builder?: boolean;
};
export type Task = {
  no: number; agent: string; task: string; acceptance: string[]; status: string; attempts: number;
  verdict: string | null; attempt_log: Attempt[]; traces: number; fitness: number | null; provisional?: boolean;
  scores: Score[];
};
export type Mission = {
  id: string; brief: string; mode: string; status: string; summary: string | null; started_at: string;
  finished_at: string | null; tasks: Task[];
};
export type Candidate = {
  index: number; target: string; lint_ok: boolean; problems: string[]; fitness: number | null;
  paired_delta?: number | null; shared_tasks?: number;
  per_task: { task: string; fitness: number | null; failure: string; critique: string }[];
};
export type Evolution = {
  id: number; agent: string; parent_version: number; winner_version: number | null; delta: number | null;
  created_at: string; parent_fitness?: number | null;
  bank?: { task: string; source: string; parent_fitness: number | null }[];
  candidates: Candidate[]; diagnosis: string | null;
};
export type Summary = {
  generated_at: string; evolvra_version: string; agents: number; versions: number; missions: number; tasks: number;
  evolutions: number; promotions: number; providers: { provider: string; requests: number; tokens: number }[];
};
export type Data = { agents: Agent[]; missions: Mission[]; evolutions: Evolution[]; summary: Summary };

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

/* ---------- formatting ---------- */
export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "–" : `${(v * 100).toFixed(digits)}%`;
export const signedPct = (v: number | null | undefined) =>
  v == null ? "–" : `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1)}%`;
export const humanize = (s: string | null | undefined) =>
  !s ? "" : s.replace(/[_-]+/g, " ").replace(/\b\w/, (c) => c.toUpperCase());
export const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "–";

export function relTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  const units: [number, string][] = [[60, "minute"], [3600, "hour"], [86400, "day"], [604800, "week"]];
  let out = "";
  for (let i = units.length - 1; i >= 0; i--) {
    const [sec, name] = units[i];
    if (diff >= sec) { const n = Math.floor(diff / sec); out = `${n} ${name}${n > 1 ? "s" : ""} ago`; break; }
  }
  return out || "just now";
}

export type Tone = "good" | "warn" | "bad" | "none";
export function grade(f: number | null | undefined): { label: string; tone: Tone } {
  if (f == null) return { label: "Not scored", tone: "none" };
  if (f >= 0.9) return { label: "Strong", tone: "good" };
  if (f >= 0.75) return { label: "Solid", tone: "warn" };
  return { label: "Needs work", tone: "bad" };
}
export const toneVar: Record<Tone, string> = { good: "var(--good)", warn: "var(--warn)", bad: "var(--bad)", none: "var(--muted)" };

/* Division identity colors: dark-step categorical slots from the validated reference palette, fixed order. */
const DIVISIONS: Record<string, string> = {
  engineering: "#3987e5", marketing: "#d95926", testing: "#199e70", product: "#9085e9",
  design: "#d55181", sales: "#c98500", security: "#e66767", support: "#008300",
};
export const divisionColor = (d: string) => DIVISIONS[d] ?? "#9085e9";

export function description(a: Agent): string {
  const cur = a.versions.find((v) => v.version === a.current_version);
  return (/^description:\s*(.+)$/m.exec(cur?.content ?? "")?.[1] ?? "").replace(/^["']|["']$/g, "");
}

export function latestPromotion(d: Data) {
  const promo = [...d.evolutions].reverse().find((e) => e.winner_version != null);
  if (!promo) return null;
  const agent = d.agents.find((a) => a.slug === promo.agent);
  if (!agent) return null;
  const parent = agent.versions.find((v) => v.version === promo.parent_version) ?? null;
  const winner = agent.versions.find((v) => v.version === promo.winner_version) ?? null;
  const cand = promo.candidates.find((c) => c.lint_ok && c.paired_delta != null && c.paired_delta === promo.delta) ?? null;
  return { promo, agent, parent, winner, cand };
}

/** The lines a version added, cleaned of markdown, for "what changed" summaries. */
export function addedLines(a: string, b: string, limit = 5): string[] {
  const clean = (raw: string) => raw.replace(/^#+\s*/, "").replace(/^[-*]\s+/, "").replace(/\*\*|`/g, "").trim();
  // a renumbered heading ("STEP 3: X" -> "STEP 4: X") is not something the agent learned
  const key = (line: string) => line.toLowerCase().replace(/\d+/g, "#").replace(/\s+/g, " ");
  const parts = diffLines(a, b);
  const removed = new Set(parts.filter((p) => p.removed).flatMap((p) => p.value.split("\n").map((l) => key(clean(l)))));
  const existing = new Set(a.split("\n").map((l) => key(clean(l))));
  const out: string[] = [];
  for (const part of parts) {
    if (!part.added) continue;
    for (const raw of part.value.split("\n")) {
      const line = clean(raw);
      if (line.length > 12 && !/^\(.*\)$/.test(line) && !removed.has(key(line)) && !existing.has(key(line))) out.push(line);
    }
  }
  return out.slice(0, limit);
}

export const providerName = (judge: string) => {
  const [provider, ...rest] = judge.split("/");
  const model = rest.join("/") || provider;
  const short = model.replace(/:free$/, "").split("/").pop() ?? model;
  return { provider, model: short };
};
