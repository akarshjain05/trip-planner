import { motion } from "framer-motion";
import { useMemo, useEffect, useRef } from "react";
import type { AgentProgressEvent } from "../types";

const AGENT_LABELS: Record<string, string> = {
  requirement_extractor: "REQUIREMENTS",
  missing_info_checker: "REQUIREMENTS CHECK",
  destination_research: "DESTINATION",
  flight_research: "FLIGHTS",
  hotel_research: "HOTELS",
  places_research: "PLACES",
  food_research: "FOOD",
  transportation: "TRANSPORT",
  weather_season: "WEATHER",
  budget_optimizer: "BUDGET",
  itinerary_generator: "ITINERARY",
  critic: "CRITIC",
  replanner: "REPLANNER",
  finalize: "FINAL CHECK",
};

const ORDER = Object.keys(AGENT_LABELS);

type Status = "pending" | "boarding" | "departed" | "revising";

function deriveStatuses(events: AgentProgressEvent[]): Record<string, Status> {
  const statuses: Record<string, Status> = {};
  for (const e of events) {
    if (!e.agent || !(e.agent in AGENT_LABELS)) continue;
    if (e.type === "agent_started" || e.type === "tool_started") {
      statuses[e.agent] = "boarding";
    } else if (e.type === "agent_completed" || e.type === "tool_completed" || e.type === "critic_result" || e.type === "budget_updated") {
      statuses[e.agent] = "departed";
    }
  }
  // A replanning event means everything from here needed another pass.
  const lastReplan = [...events].reverse().find((e) => e.type === "replanning");
  if (lastReplan) {
    const targets = (lastReplan.payload?.resuming_from as string[]) ?? [];
    for (const t of targets) {
      if (t in AGENT_LABELS) statuses[t] = "revising";
    }
  }
  return statuses;
}

const STATUS_STYLE: Record<Status, { label: string; className: string }> = {
  pending: { label: "waiting", className: "text-text-faint" },
  boarding: { label: "working", className: "text-accent animate-pulse" },
  departed: { label: "done", className: "text-jade" },
  revising: { label: "revising", className: "text-stamp" },
};

export function AgentProgressBoard({ events }: { events: AgentProgressEvent[] }) {
  const statuses = useMemo(() => deriveStatuses(events), [events]);
  const iteration = events.filter((e) => e.type === "replanning").length;

  const messages = events.filter((e) => e.message);
  const recentMessages = messages.slice(-50);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <motion.div layout className="rounded-2xl border border-border-soft bg-surface p-5">
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="label-eyebrow">Agent execution</span>
        {iteration > 0 && (
          <span className="font-mono text-[10px] text-stamp">REVISION {iteration}</span>
        )}
      </div>

      <div className="rounded-lg bg-bg border border-border overflow-hidden mb-4">
        <div className="grid grid-cols-[1fr_auto] gap-x-4 px-4 py-2.5 border-b border-border">
          <span className="font-mono text-[10px] text-text-faint tracking-widest">AGENT</span>
          <span className="font-mono text-[10px] text-text-faint tracking-widest">STATUS</span>
        </div>
        {ORDER.map((key) => {
          const status = statuses[key] ?? "pending";
          const style = STATUS_STYLE[status];
          return (
            <div
              key={key}
              className="grid grid-cols-[1fr_auto] gap-x-4 px-4 py-2.5 border-b border-border last:border-b-0"
            >
              <span className={`font-mono text-xs tracking-wide ${status === "pending" ? "text-text-faint" : "text-text"}`}>
                {AGENT_LABELS[key]}
              </span>
              <span className={`font-mono text-xs tracking-wide uppercase ${style.className}`}>{style.label}</span>
            </div>
          );
        })}
      </div>

      {recentMessages.length > 0 && (
        <div className="rounded-lg bg-[#0a0a0a] border border-border-soft overflow-hidden flex flex-col">
          <div className="px-3 py-2 border-b border-white/5 flex items-center gap-2 bg-[#111]">
             <div className="flex gap-1.5">
               <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
               <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
               <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
             </div>
             <span className="font-mono text-[9px] text-white/30 uppercase tracking-widest ml-2">Live Agent Logs</span>
          </div>
          <div 
            ref={scrollRef}
            className="h-40 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed flex flex-col gap-1 scroll-smooth"
          >
            {recentMessages.map((msg, idx) => (
              <div key={idx} className="flex gap-3">
                <span className="text-white/30 shrink-0">
                  {new Date(msg.ts).toISOString().substring(11, 19)}
                </span>
                <span className={msg.type === "message" ? "text-white/60 break-all" : "text-accent"}>
                  {msg.agent ? `[${AGENT_LABELS[msg.agent] || msg.agent}] ` : ""}
                  {msg.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
  </motion.div>
  );
}