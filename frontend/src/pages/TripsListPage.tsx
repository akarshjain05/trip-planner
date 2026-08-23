import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listTrips } from "../services/api";
import type { TripStatus } from "../types";

const STATUS_LABEL: Record<TripStatus, string> = {
  draft: "Draft",
  awaiting_input: "Needs your input",
  planning: "Planning...",
  completed: "Ready",
  failed: "Failed",
};

const STATUS_COLOR: Record<TripStatus, string> = {
  draft: "text-text-faint",
  awaiting_input: "text-accent",
  planning: "text-accent animate-pulse",
  completed: "text-jade",
  failed: "text-stamp",
};

export function TripsListPage() {
  const { data: trips, isLoading } = useQuery({ queryKey: ["trips"], queryFn: listTrips });

  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <div className="flex items-center justify-between mb-10">
        <div>
          <p className="label-eyebrow mb-2">Your trips</p>
          <h1 className="font-display text-3xl text-text">Everywhere you're headed</h1>
        </div>
        <Link
          to="/trips/new"
          className="px-5 py-2.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors text-sm"
        >
          Plan a trip
        </Link>
      </div>

      {isLoading && <p className="text-text-muted text-sm">Loading...</p>}

      {!isLoading && trips?.length === 0 && (
        <div className="border border-dashed border-border-soft rounded-2xl p-12 text-center">
          <p className="text-text-muted mb-4">No trips yet -- describe one and watch it get planned.</p>
          <Link to="/trips/new" className="text-accent hover:text-accent-soft text-sm">
            Plan your first trip &rarr;
          </Link>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {trips?.map((trip) => (
          <Link
            key={trip.id}
            to={`/trips/${trip.id}`}
            className="block border border-border-soft rounded-xl px-6 py-5 bg-surface hover:border-accent/50 transition-colors"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-text font-medium truncate">{trip.title}</p>
                <p className="text-text-faint text-xs mt-1 font-mono">
                  {new Date(trip.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                </p>
              </div>
              <span className={`font-mono text-xs uppercase tracking-wide whitespace-nowrap ${STATUS_COLOR[trip.status]}`}>
                {STATUS_LABEL[trip.status]}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
