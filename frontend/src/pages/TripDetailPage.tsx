import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import type { FormEvent } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getBudget, getItinerary, getSources, getTrip, getTripStatus,
  modifyTrip, planTrip, regenerateTrip,
} from "../services/api";
import { useAgentStream } from "../hooks/useAgentStream";
import { AgentProgressBoard } from "../components/AgentProgressBoard";
import { ItineraryDayCard } from "../components/ItineraryDayCard";
import { BudgetChart } from "../components/BudgetChart";

export function TripDetailPage() {
  const { tripId = "" } = useParams();
  const queryClient = useQueryClient();

  const { data: trip } = useQuery({ queryKey: ["trip", tripId], queryFn: () => getTrip(tripId), enabled: !!tripId });

  const { data: status } = useQuery({
    queryKey: ["trip-status", tripId],
    queryFn: () => getTripStatus(tripId),
    enabled: !!tripId,
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "planning" ? 1500 : false;
    },
  });

  const isPlanning = status?.status === "planning";
  const { events } = useAgentStream(tripId, status?.latest_agent_run_id, isPlanning);

  // Once planning finishes, make sure dependent data refetches.
  const [lastKnownStatus, setLastKnownStatus] = useState<string | undefined>();
  if (status && status.status !== lastKnownStatus) {
    if (lastKnownStatus === "planning") {
      queryClient.invalidateQueries({ queryKey: ["itinerary", tripId] });
      queryClient.invalidateQueries({ queryKey: ["budget", tripId] });
      queryClient.invalidateQueries({ queryKey: ["sources", tripId] });
    }
    setLastKnownStatus(status.status);
  }

  const showResults = status?.status === "completed";

  const { data: itinerary, isError: isItineraryError } = useQuery({
    queryKey: ["itinerary", tripId], queryFn: () => getItinerary(tripId), enabled: showResults, retry: false,
  });
  const { data: budget } = useQuery({
    queryKey: ["budget", tripId], queryFn: () => getBudget(tripId), enabled: showResults,
  });
  const { data: sources } = useQuery({
    queryKey: ["sources", tripId], queryFn: () => getSources(tripId), enabled: showResults,
  });

  const isFailed = status?.status === "failed" || (status?.status === "completed" && isItineraryError);
  const isLoading = !trip || !status;

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <p className="label-eyebrow mb-2">Trip</p>
      <h1 className="font-display text-3xl text-text mb-10">{trip.title}</h1>

      <AnimatePresence>
        {status.status === "draft" && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }}>
            <StartPlanning tripId={tripId} onStarted={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })} />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {status.status === "awaiting_input" && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}>
            <ClarifyingQuestion
              tripId={tripId}
              question={status.clarifying_question}
              onAnswered={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isPlanning && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="mb-10 overflow-hidden">
            <AgentProgressBoard events={events} />
            <div className="mt-4 flex justify-end">
              <RegenerateButton tripId={tripId} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {isFailed && (
        <div className="border border-stamp/40 bg-stamp/10 rounded-xl px-6 py-5 text-sm text-text">
          Something went wrong while planning this trip. You can try regenerating it.
          <div className="mt-4">
            <RegenerateButton tripId={tripId} />
          </div>
        </div>
      )}

      <AnimatePresence>
        {showResults && itinerary && budget && (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, staggerChildren: 0.1 }}
            className="flex flex-col gap-8"
          >
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
              <BudgetChart budget={budget} />
            </motion.div>

            <div className="flex flex-col gap-6">
              {itinerary.days.map((day, i) => (
                <motion.div 
                  key={day.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2 + (i * 0.1) }}
                >
                  <ItineraryDayCard day={day} currency={itinerary.currency} tripId={tripId} />
                </motion.div>
              ))}
            </div>

            {sources && sources.length > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
                <Sources sources={sources} />
              </motion.div>
            )}

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
              <ModifyBox tripId={tripId} onSubmitted={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })} />
            </motion.div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }} className="flex justify-end">
              <RegenerateButton tripId={tripId} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StartPlanning({ tripId, onStarted }: { tripId: string; onStarted: () => void }) {
  const [loading, setLoading] = useState(false);
  return (
    <button
      onClick={async () => {
        setLoading(true);
        await planTrip(tripId);
        onStarted();
      }}
      disabled={loading}
      className="px-6 py-3 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-60"
    >
      {loading ? "Starting..." : "Start planning"}
    </button>
  );
}

function ClarifyingQuestion({
  tripId, question, onAnswered,
}: { tripId: string; question: string | null; onAnswered: () => void }) {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!answer.trim()) return;
    setLoading(true);
    await planTrip(tripId, answer.trim());
    onAnswered();
  }

  return (
    <div className="border border-accent/40 bg-accent/10 rounded-xl px-6 py-5 mb-10">
      <p className="text-text mb-4">{question ?? "A couple more details would help."}</p>
      <form onSubmit={onSubmit} className="flex gap-3">
        <input
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          autoFocus
          className="flex-1 bg-surface border border-border-soft rounded-lg px-4 py-2.5 text-text placeholder:text-text-faint focus:border-accent transition-colors outline-none"
          placeholder="Your answer..."
          aria-label="Your answer to the clarifying question"
        />
        <button
          type="submit"
          disabled={loading || !answer.trim()}
          className="px-5 py-2.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-60"
        >
          {loading ? "..." : "Continue"}
        </button>
      </form>
    </div>
  );
}

function ModifyBox({ tripId, onSubmitted }: { tripId: string; onSubmitted: () => void }) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setLoading(true);
    await modifyTrip(tripId, message.trim());
    setMessage("");
    onSubmitted();
  }

  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-6">
      <p className="label-eyebrow mb-3">Want something different?</p>
      <form onSubmit={onSubmit} className="flex gap-3">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder='"Hotels are too expensive." "Remove the museums." "Change Tokyo to Kyoto."'
          aria-label="Describe what you want to change"
          className="flex-1 bg-bg border border-border-soft rounded-lg px-4 py-2.5 text-text placeholder:text-text-faint focus:border-accent transition-colors outline-none text-sm"
        />
        <button
          type="submit"
          disabled={loading || !message.trim()}
          className="px-5 py-2.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-60 text-sm shrink-0"
        >
          {loading ? "Updating..." : "Update plan"}
        </button>
      </form>
    </div>
  );
}

function RegenerateButton({ tripId }: { tripId: string }) {
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState(false);
  return (
    <button
      onClick={async () => {
        setLoading(true);
        try {
          await regenerateTrip(tripId);
          queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] });
        } finally {
          setLoading(false);
        }
      }}
      disabled={loading}
      className="text-xs text-text-faint hover:text-text-muted transition-colors font-mono uppercase tracking-wide disabled:opacity-60"
    >
      {loading ? "Regenerating..." : "Regenerate whole itinerary"}
    </button>
  );
}

function Sources({ sources }: { sources: { url: string; title: string | null; source: string | null }[] }) {
  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-6">
      <p className="label-eyebrow mb-3">Sources consulted</p>
      <ul className="flex flex-col gap-1.5">
        {sources.map((s) => (
          <li key={s.url} className="text-xs">
            <a href={s.url} target="_blank" rel="noreferrer" className="text-text-muted hover:text-accent transition-colors">
              {s.title ?? s.url}
            </a>
            {s.source && <span className="text-text-faint"> &middot; {s.source}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
