import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentProgressEvent } from "../types";
import { streamUrl, getAgentRun } from "../services/api";

export function useAgentStream(tripId: string | null, runId: string | null | undefined, active: boolean) {
  const [events, setEvents] = useState<AgentProgressEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => setEvents([]), []);

  useEffect(() => {
    if (!tripId || !active) return;

    let isMounted = true;

    const connectStream = () => {
      const es = new EventSource(streamUrl(tripId));
      sourceRef.current = es;

      es.onopen = () => {
        if (isMounted) setConnected(true);
      };
      es.onerror = () => {
        if (isMounted) setConnected(false);
      };

      const handler = (e: MessageEvent) => {
        if (!isMounted) return;
        try {
          const parsed: AgentProgressEvent = JSON.parse(e.data);
          setEvents((prev) => [...prev, parsed]);
        } catch {
          // ignore malformed frames
        }
      };

      const knownTypes = [
        "agent_started", "agent_completed", "tool_started", "tool_completed",
        "search_result", "budget_updated", "critic_result", "replanning",
        "finalizing", "completed", "error", "message",
      ];
      knownTypes.forEach((t) => es.addEventListener(t, handler));

      return () => {
        knownTypes.forEach((t) => es.removeEventListener(t, handler));
        es.close();
        if (isMounted) {
          sourceRef.current = null;
          setConnected(false);
        }
      };
    };

    if (runId) {
      getAgentRun(runId).then((runData) => {
        if (!isMounted) return;
        const history = (runData.events || []).map((e: any) => ({
          type: e.event_type,
          agent: e.agent_name,
          message: e.message,
          payload: e.payload,
          ts: new Date(e.created_at).getTime(),
        }));
        setEvents(history);
        connectStream();
      }).catch((err) => {
        console.error("Failed to fetch historical events", err);
        if (isMounted) connectStream();
      });
    } else {
      connectStream();
    }

    return () => {
      isMounted = false;
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, [tripId, runId, active]);

  return { events, connected, reset };
}
