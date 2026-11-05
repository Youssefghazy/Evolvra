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
        <div className="mb-5 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:flex-wrap sm:items-center sm:gap-2">
          <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
          <LayoutGroup>
            {["all", ...divisions].map((d) => (
              <button key={d} onClick={() => setDiv(d)}
                className={`relative h-9 shrink-0 rounded-full border px-3.5 text-xs capitalize transition-colors sm:h-auto sm:border-transparent sm:px-3 sm:py-1.5 ${div === d ? "border-transparent text-ink" : "border-line text-muted hover:text-ink"}`}>
                {div === d && <motion.span layoutId="div-pill" className="absolute inset-0 rounded-full border border-line-strong bg-card-hover" />}
                <span className="relative inline-flex items-center gap-1.5">
                  {d !== "all" && <span className="h-1.5 w-1.5 rounded-full" style={{ background: divisionColor(d) }} />}{d}
                </span>
              </button>
            ))}
          </LayoutGroup>
          </div>
          <div className="flex items-center gap-1 self-start rounded-full border border-line bg-card p-1 text-xs sm:ml-auto">
            {(["fitness", "weakest", "name"] as Sort[]).map((s) => (
              <button key={s} onClick={() => setSort(s)}
                className={`h-8 rounded-full px-3 capitalize transition-colors sm:h-auto sm:px-2.5 sm:py-1 ${sort === s ? "bg-card-hover text-ink" : "text-muted hover:text-ink"}`}>{s === "fitness" ? "strongest" : s}</button>
            ))}
          </div>
        </div>
      </Reveal>
      <motion.div layout className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
        {list.map((a, i) => {
          const cur = a.versions.find((v) => v.version === a.current_version);
          const g = grade(a.fitness);
          return (
            <motion.div key={a.slug} layout transition={{ type: "spring", stiffness: 300, damping: 30 }}>
              <Reveal delay={Math.min(i, 8) * 0.04} className="h-full">
                <CometCard rotateDepth={6} translateDepth={6} glare="hover" glareOpacity={0.28} className="h-full">
                <Spotlight href={href.agent(a.slug)} arrow={false} className="flex h-full flex-col p-4 sm:p-5">
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
                  <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-ink2 sm:mt-4 sm:line-clamp-3">{description(a)}</p>
                  <div className="mt-auto flex flex-wrap items-center gap-2 pt-4 text-xs text-muted sm:pt-5">
                    <span>{a.tasks} task{a.tasks === 1 ? "" : "s"}</span>
                    <span>·</span>
                    <span className="text-ink2">{g.label}</span>
                    {a.versions.length > 1 && <Chip tone="var(--good)" className="ml-auto"><GitBranch size={11} /> evolved to v{a.current_version}</Chip>}
                    {a.versions.length === 1 && cur?.top_failure && <Chip className="ml-auto"
                      title={cur.top_failure_contested ? "Raised by only one judge; the other two found every criterion met" : "Most common issue the judges raised"}>
                      {humanize(cur.top_failure)}{cur.top_failure_contested && <span className="text-muted">· contested</span>}</Chip>}
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
