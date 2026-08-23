import { useMemo } from "react";
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
  const latestMessage = [...events].reverse().find((e) => e.message)?.message;
  const iteration = events.filter((e) => e.type === "replanning").length;

  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-5">
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="label-eyebrow">Agent execution</span>
        {iteration > 0 && (
          <span className="font-mono text-[10px] text-stamp">REVISION {iteration}</span>
        )}
      </div>

      <div className="rounded-lg bg-bg border border-border overflow-hidden">
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

      {latestMessage && (
        <p className="text-xs text-text-muted mt-3 px-1 leading-relaxed">{latestMessage}</p>
      )}
    </div>
  );
}
