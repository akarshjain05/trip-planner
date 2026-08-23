import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createTrip, planTrip } from "../services/api";

const EXAMPLES = [
  "I want to visit Japan for 8 days in October. My budget is \u20b91,50,000. I like nature, anime, food and photography. I don't like crowded tourist attractions. I am traveling with one friend. I prefer comfortable hotels and don't want extremely long travel days. I'm flying from Mumbai.",
  "Long weekend in Lisbon for two, food-focused, avoid the touristy spots, flying from Delhi, budget around \u20b980,000.",
  "10-day New Zealand road trip from Bangalore, adventure heavy -- hiking, kayaking -- moderate budget, relaxed pace.",
];

export function NewTripPage() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const trip = await createTrip(prompt.trim());
      await planTrip(trip.id);
      navigate(`/trips/${trip.id}`);
    } catch {
      setError("Couldn't start planning that trip. Try again in a moment.");
      setIsSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-16">
      <p className="label-eyebrow mb-2">New trip</p>
      <h1 className="font-display text-3xl sm:text-4xl text-text mb-3">Where to, and what matters?</h1>
      <p className="text-text-muted mb-8 leading-relaxed">
        Write it like you'd tell a friend: destination, dates or duration, budget,
        who's coming, and what you love or want to avoid. The more specific, the
        better the first draft.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={7}
          required
          placeholder="I want to visit..."
          className="bg-surface border border-border-soft rounded-xl px-5 py-4 text-text placeholder:text-text-faint focus:border-accent transition-colors outline-none resize-none leading-relaxed"
        />
        {error && <p className="text-sm text-stamp">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting || !prompt.trim()}
          className="self-start px-7 py-3 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-50"
        >
          {isSubmitting ? "Starting..." : "Start planning"}
        </button>
      </form>

      <div className="mt-12">
        <p className="label-eyebrow mb-3">Or start from an example</p>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setPrompt(ex)}
              className="text-left font-mono text-xs text-text-muted border border-border-soft rounded-lg px-4 py-3 bg-surface/50 hover:border-accent/50 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
