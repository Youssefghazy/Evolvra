import { divisionColor, grade, pct, toneVar, type Agent } from "../data";
import { CometCard } from "./ui/comet-card";
import { LogoMark } from "./Logo";
import { roleIcon } from "./ui";

/** A collectible "agent passport" in the shape of the Comet Card demo: portrait card, art panel, mono footer. */
export default function AgentPassport({ agent }: { agent: Agent }) {
  const c = divisionColor(agent.division);
  const Icon = roleIcon(agent);
  const g = grade(agent.fitness);
  const cur = agent.versions.find((v) => v.version === agent.current_version);
  const code = (cur?.sha ?? agent.slug).slice(0, 4).toUpperCase();
  return (
    <CometCard rotateDepth={14} translateDepth={14}>
      <div className="flex w-64 cursor-default flex-col items-stretch rounded-[16px] border border-white/10 bg-[#141418] p-2 md:p-3"
        style={{ transformStyle: "preserve-3d", transform: "none", opacity: 1 }} aria-label={`${agent.name} passport`}>
        <div className="mx-1 flex-1">
          <div className="relative mt-1 aspect-[3/4] w-full overflow-hidden rounded-[14px]"
            style={{ background: `radial-gradient(120% 90% at 30% 15%, color-mix(in srgb, ${c} 55%, #0b0b10), #07070a 70%)` }}>
            <div className="absolute inset-0 opacity-[0.18]"
              style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)", backgroundSize: "18px 18px", maskImage: "radial-gradient(circle at 50% 40%, #000, transparent 75%)" }} />
            <div className="absolute left-3 top-3 text-white/80"><LogoMark size={20} /></div>
            <div className="absolute right-3 top-3 rounded-full border border-white/15 bg-black/30 px-2 py-0.5 font-mono text-[10px] text-white/80">v{agent.current_version}</div>
            <div className="absolute inset-0 grid place-items-center">
              <Icon size={84} strokeWidth={1.1} style={{ color: `color-mix(in srgb, ${c} 45%, white)`, filter: `drop-shadow(0 0 24px ${c})` }} />
            </div>
            <div className="absolute inset-x-3 bottom-3">
              <div className="text-lg font-semibold leading-tight text-white">{agent.name}</div>
              <div className="mt-0.5 text-[11px] uppercase tracking-[0.18em] text-white/60">{agent.division}</div>
            </div>
          </div>
        </div>
        <div className="mt-2 flex flex-shrink-0 items-center justify-between px-3 py-2 font-mono text-white">
          <div className="text-xs">fitness <span style={{ color: toneVar[g.tone] }}>{pct(agent.fitness)}</span></div>
          <div className="text-xs text-gray-300 opacity-50">#{code}</div>
        </div>
      </div>
    </CometCard>
  );
}
