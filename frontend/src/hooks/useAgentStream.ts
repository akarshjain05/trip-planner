import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentProgressEvent } from "../types";
import { streamUrl } from "../services/api";

/**
 * Subscribes to the live SSE agent-progress stream for a trip. Kept as a
 * small dedicated hook (rather than inlined in the page) so the Agent
 * Execution View and any future consumer (e.g. a notifications bell)
 * can share one connection-management implementation.
 */
export function useAgentStream(tripId: string | null, active: boolean) {
  const [events, setEvents] = useState<AgentProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!tripId || !active) return;

    const es = new EventSource(streamUrl(tripId));
    sourceRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    const handler = (e: MessageEvent) => {
      try {
        const parsed: AgentProgressEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, parsed]);
      } catch {
        // ignore malformed frames
      }
    };

    // The server sets `event: <type>` per frame; listen broadly by
    // attaching the same handler to every known type plus the default.
    const knownTypes = [
      "agent_started", "agent_completed", "tool_started", "tool_completed",
      "search_result", "budget_updated", "critic_result", "replanning",
      "finalizing", "completed", "error", "message",
    ];
    knownTypes.forEach((t) => es.addEventListener(t, handler));

    return () => {
      knownTypes.forEach((t) => es.removeEventListener(t, handler));
      es.close();
      sourceRef.current = null;
      setConnected(false);
    };
  }, [tripId, active]);

  return { events, connected, reset };
}
