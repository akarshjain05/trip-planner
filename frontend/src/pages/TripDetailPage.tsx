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
  const { events } = useAgentStream(tripId, isPlanning);

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

  const { data: itinerary } = useQuery({
    queryKey: ["itinerary", tripId], queryFn: () => getItinerary(tripId), enabled: showResults,
  });
  const { data: budget } = useQuery({
    queryKey: ["budget", tripId], queryFn: () => getBudget(tripId), enabled: showResults,
  });
  const { data: sources } = useQuery({
    queryKey: ["sources", tripId], queryFn: () => getSources(tripId), enabled: showResults,
  });

  if (!trip || !status) {
    return <div className="max-w-3xl mx-auto px-6 py-16 text-text-muted text-sm">Loading trip...</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <p className="label-eyebrow mb-2">Trip</p>
      <h1 className="font-display text-3xl text-text mb-10">{trip.title}</h1>

      {status.status === "draft" && (
        <StartPlanning tripId={tripId} onStarted={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })} />
      )}

      {status.status === "awaiting_input" && (
        <ClarifyingQuestion
          tripId={tripId}
          question={status.clarifying_question}
          onAnswered={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })}
        />
      )}

      {isPlanning && (
        <div className="mb-10">
          <AgentProgressBoard events={events} />
        </div>
      )}

      {status.status === "failed" && (
        <div className="border border-stamp/40 bg-stamp/10 rounded-xl px-6 py-5 text-sm text-text">
          Something went wrong while planning this trip. You can try regenerating it.
          <div className="mt-4">
            <RegenerateButton tripId={tripId} />
          </div>
        </div>
      )}

      {showResults && itinerary && budget && (
        <div className="flex flex-col gap-8">
          <BudgetChart budget={budget} />

          <div className="flex flex-col gap-6">
            {itinerary.days.map((day) => (
              <ItineraryDayCard key={day.id} day={day} currency={itinerary.currency} />
            ))}
          </div>

          {sources && sources.length > 0 && <Sources sources={sources} />}

          <ModifyBox tripId={tripId} onSubmitted={() => queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] })} />

          <div className="flex justify-end">
            <RegenerateButton tripId={tripId} />
          </div>
        </div>
      )}
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
        await regenerateTrip(tripId);
        queryClient.invalidateQueries({ queryKey: ["trip-status", tripId] });
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
