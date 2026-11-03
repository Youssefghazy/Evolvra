import { type Data, divisionColor } from "../data";
import { Fitness } from "./ui";

export default function Roster({ data }: { data: Data }) {
  const divisions = [...new Set(data.agents.map((a) => a.division))];
  return (
    <div className="grid gap-6">
      {divisions.map((d) => (
        <section key={d}>
          <h2 className="text-sm font-medium uppercase tracking-wide mb-3" style={{ color: divisionColor(d) }}>{d}</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.agents.filter((a) => a.division === d).map((a) => {
              const cur = a.versions.find((v) => v.version === a.current_version);
              const desc = (/^description:\s*(.+)$/m.exec(cur?.content ?? "")?.[1] ?? "").replace(/^["']|["']$/g, "");
              return (
                <a key={a.slug} href={`#/agent/${a.slug}`} className="panel p-4 hover:-translate-y-0.5 transition-transform" style={{ borderTop: `3px solid ${divisionColor(d)}` }}>
                  <div className="flex items-center justify-between">
                    <div className="font-medium">{a.emoji} {a.name}</div>
                    <span className="chip mono">v{a.current_version}</span>
                  </div>
                  <p className="text-xs muted mt-2 line-clamp-3">{desc}</p>
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <Fitness value={a.fitness} />
                    <span className="muted">{a.tasks} tasks · {a.versions.length} ver.</span>
                  </div>
                </a>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
