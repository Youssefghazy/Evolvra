import { useMemo, useState } from "react";
import { motion, LayoutGroup } from "motion/react";
import { GitBranch } from "lucide-react";
import { description, divisionColor, grade, humanize, type Data } from "../data";
import { href } from "../lib/router";
import { Reveal, Spotlight } from "../components/fx";
import { Avatar, Chip, DivisionChip, Ring, SectionHeader } from "../components/ui";
import { CometCard } from "../components/ui/comet-card";

type Sort = "fitness" | "weakest" | "name";

export default function Agents({ data }: { data: Data }) {
  const divisions = useMemo(() => [...new Set(data.agents.map((a) => a.division))], [data]);
  const [div, setDiv] = useState<string>("all");
  const [sort, setSort] = useState<Sort>("fitness");
  const list = useMemo(() => {
    const l = data.agents.filter((a) => div === "all" || a.division === div);
    return [...l].sort((x, y) =>
      sort === "name" ? x.name.localeCompare(y.name)
        : sort === "weakest" ? (x.fitness ?? 2) - (y.fitness ?? 2)
          : (y.fitness ?? -1) - (x.fitness ?? -1));
  }, [data, div, sort]);
  const evolved = data.agents.filter((a) => a.versions.length > 1).length;

  return (
    <div>
      <Reveal>
        <SectionHeader eyebrow="The roster" title={<>{data.agents.length} specialists, {evolved} evolved so far</>}
          sub="Each agent is a persona file from the open-source agency-agents library. Evolution rewrites these files, and every version is kept." />
      </Reveal>
      <Reveal delay={0.05}>
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <LayoutGroup>
            {["all", ...divisions].map((d) => (
              <button key={d} onClick={() => setDiv(d)}
                className={`relative rounded-full px-3 py-1.5 text-xs capitalize transition-colors ${div === d ? "text-ink" : "text-muted hover:text-ink"}`}>
                {div === d && <motion.span layoutId="div-pill" className="absolute inset-0 rounded-full border border-line-strong bg-card-hover" />}
                <span className="relative inline-flex items-center gap-1.5">
                  {d !== "all" && <span className="h-1.5 w-1.5 rounded-full" style={{ background: divisionColor(d) }} />}{d}
                </span>
              </button>
            ))}
          </LayoutGroup>
          <div className="ml-auto flex items-center gap-1 rounded-full border border-line bg-card p-1 text-xs">
            {(["fitness", "weakest", "name"] as Sort[]).map((s) => (
              <button key={s} onClick={() => setSort(s)}
                className={`rounded-full px-2.5 py-1 capitalize ${sort === s ? "bg-card-hover text-ink" : "text-muted"}`}>{s === "fitness" ? "strongest" : s}</button>
            ))}
          </div>
        </div>
      </Reveal>
      <motion.div layout className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((a, i) => {
          const cur = a.versions.find((v) => v.version === a.current_version);
          const g = grade(a.fitness);
          return (
            <motion.div key={a.slug} layout transition={{ type: "spring", stiffness: 300, damping: 30 }}>
              <Reveal delay={Math.min(i, 8) * 0.04} className="h-full">
                <CometCard rotateDepth={6} translateDepth={6} glare="hover" glareOpacity={0.28} className="h-full">
                <Spotlight as="a" href={href.agent(a.slug)} className="flex h-full flex-col p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <Avatar agent={a} size={46} />
                      <div>
                        <div className="font-semibold leading-tight">{a.name}</div>
                        <div className="mt-1.5"><DivisionChip division={a.division} /></div>
                      </div>
                    </div>
                    <Ring value={a.fitness} size={54} stroke={5} />
                  </div>
                  <p className="mt-4 line-clamp-3 text-sm leading-relaxed text-ink2">{description(a)}</p>
                  <div className="mt-auto flex flex-wrap items-center gap-2 pt-5 text-xs text-muted">
                    <span>{a.tasks} task{a.tasks === 1 ? "" : "s"}</span>
                    <span>·</span>
                    <span className="text-ink2">{g.label}</span>
                    {a.versions.length > 1 && <Chip tone="var(--good)" className="ml-auto"><GitBranch size={11} /> evolved to v{a.current_version}</Chip>}
                    {a.versions.length === 1 && cur?.top_failure && <Chip className="ml-auto" title="Most common issue the judges raised">{humanize(cur.top_failure)}</Chip>}
                  </div>
                </Spotlight>
                </CometCard>
              </Reveal>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
