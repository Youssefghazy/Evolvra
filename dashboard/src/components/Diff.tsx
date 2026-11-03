import { createTwoFilesPatch } from "diff";

export default function Diff({ a, b, labelA, labelB }: { a: string; b: string; labelA: string; labelB: string }) {
  const patch = createTwoFilesPatch(labelA, labelB, a, b, "", "", { context: 3 });
  const lines = patch.split("\n").slice(4);
  const changed = lines.filter((l) => /^[+-]/.test(l)).length;
  if (changed === 0) return <div className="muted text-sm">No differences.</div>;
  return (
    <pre className="mono text-xs overflow-auto rounded-lg p-3" style={{ background: "var(--panel-2)", maxHeight: 520 }}>
      {lines.map((l, i) => {
        const cls = l.startsWith("+") ? "diff-add" : l.startsWith("-") ? "diff-del" : l.startsWith("@@") ? "diff-hunk" : "";
        return <div key={i} className={cls}>{l || " "}</div>;
      })}
    </pre>
  );
}
