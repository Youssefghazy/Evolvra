import { useMemo, useState } from "react";
import { diffLines } from "diff";
import { ChevronsUpDown } from "lucide-react";

type Row = { kind: "add" | "del" | "ctx"; text: string; a?: number; b?: number } | { kind: "gap"; hidden: Row[] };

/** Unified diff with line numbers; long unchanged runs fold into an expandable gap. */
export default function Diff({ a, b, labelA, labelB }: { a: string; b: string; labelA: string; labelB: string }) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const { rows, added, removed } = useMemo(() => {
    const flat: Row[] = [];
    let ln = 1, rn = 1, added = 0, removed = 0;
    for (const part of diffLines(a, b)) {
      const lines = part.value.replace(/\n$/, "").split("\n");
      for (const text of lines) {
        if (part.added) { flat.push({ kind: "add", text, b: rn++ }); added++; }
        else if (part.removed) { flat.push({ kind: "del", text, a: ln++ }); removed++; }
        else flat.push({ kind: "ctx", text, a: ln++, b: rn++ });
      }
    }
    const out: Row[] = [];
    const CONTEXT = 3;
    let i = 0;
    while (i < flat.length) {
      if (flat[i].kind !== "ctx") { out.push(flat[i]); i++; continue; }
      let j = i;
      while (j < flat.length && flat[j].kind === "ctx") j++;
      const run = flat.slice(i, j);
      const head = i === 0 ? 0 : CONTEXT, tail = j === flat.length ? 0 : CONTEXT;
      if (run.length > head + tail + 2) {
        out.push(...run.slice(0, head), { kind: "gap", hidden: run.slice(head, run.length - tail) }, ...run.slice(run.length - tail));
      } else out.push(...run);
      i = j;
    }
    return { rows: out, added, removed };
  }, [a, b]);

  if (added === 0 && removed === 0) return <div className="py-6 text-center text-sm text-muted">These versions are identical.</div>;

  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="flex items-center justify-between border-b border-line bg-card px-3 py-2 text-xs">
        <span className="font-mono text-ink2">{labelA} → {labelB}</span>
        <span className="font-mono"><span style={{ color: "var(--good)" }}>+{added}</span> <span style={{ color: "var(--bad)" }}>−{removed}</span></span>
      </div>
      <div className="max-h-[560px] overflow-auto font-mono text-[12px] leading-6">
        {rows.map((r, idx) => {
          if (r.kind === "gap") {
            if (open.has(idx)) return r.hidden.map((h, k) => <Line key={`${idx}-${k}`} row={h} />);
            return (
              <button key={idx} onClick={() => setOpen(new Set(open).add(idx))}
                className="flex w-full items-center gap-2 bg-bg2 px-3 py-1 text-left text-[11px] text-muted hover:text-ink">
                <ChevronsUpDown size={12} /> {r.hidden.length} unchanged lines
              </button>
            );
          }
          return <Line key={idx} row={r} />;
        })}
      </div>
    </div>
  );
}

function Line({ row }: { row: Row }) {
  if (row.kind === "gap") return null;
  const cls = row.kind === "add" ? "diff-add" : row.kind === "del" ? "diff-del" : "";
  return (
    <div className={`grid grid-cols-[3rem_3rem_1.25rem_1fr] ${cls}`}>
      <span className="select-none pr-2 text-right text-muted/70">{row.a ?? ""}</span>
      <span className="select-none pr-2 text-right text-muted/70">{row.b ?? ""}</span>
      <span className="sign select-none text-center">{row.kind === "add" ? "+" : row.kind === "del" ? "−" : ""}</span>
      <span className="whitespace-pre-wrap break-words pr-4 text-ink2">{row.text || " "}</span>
    </div>
  );
}
