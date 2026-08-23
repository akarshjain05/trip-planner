import { Link } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { DepartureBoard } from "../components/DepartureBoard";

const EXAMPLE_PROMPTS = [
  "8 days in Japan, October, ₹1,50,000, into nature and anime, hate crowds",
  "Long weekend in Lisbon for two, food-focused, nothing touristy",
  "10-day New Zealand road trip, adventure heavy, moderate budget",
  "Relaxed week in Bali, one kid, need a pool and easy flights",
];

const PIPELINE_STAGES = [
  { label: "Understand", detail: "Pulls dates, budget, travelers, likes and dislikes out of what you typed -- and asks if something critical is missing." },
  { label: "Research", detail: "Separate agents look into destinations, flights, hotels, places, and food in parallel, each weighing your stated preferences." },
  { label: "Assemble", detail: "Transportation, weather, and budget agents fold their findings together into one costed, day-by-day plan." },
  { label: "Critique", detail: "A dedicated critic checks the draft for budget overruns, packed days, and violated preferences -- before you ever see it." },
  { label: "Refine", detail: "If the critic finds a real problem, only the affected agents re-run. Everything that was already right stays untouched." },
];

export function LandingPage() {
  const { user } = useAuthStore();

  return (
    <div className="bg-bg">
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="max-w-6xl mx-auto px-6 pt-20 pb-24 grid lg:grid-cols-[1.1fr_0.9fr] gap-16 items-center">
          <div>
            <p className="label-eyebrow mb-5">An agentic travel planner</p>
            <h1 className="font-display text-5xl sm:text-6xl leading-[1.05] text-text mb-6">
              Your AI travel agent
              <br />
              that <em className="text-accent not-italic">actually plans</em>.
            </h1>
            <p className="text-text-muted text-lg max-w-lg mb-9 leading-relaxed">
              Not a chatbot that guesses at an itinerary in one breath. A team of
              research agents that search, price, critique their own work, and
              redo exactly what's wrong -- until the plan holds up.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                to={user ? "/trips/new" : "/register"}
                className="px-7 py-3 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors"
              >
                Plan a trip
              </Link>
              <a href="#how-it-thinks" className="text-text-muted hover:text-text transition-colors text-sm">
                See how it thinks &darr;
              </a>
            </div>

            <div className="mt-12">
              <p className="label-eyebrow mb-3">Try a prompt like</p>
              <div className="flex flex-col gap-2">
                {EXAMPLE_PROMPTS.map((p) => (
                  <div
                    key={p}
                    className="font-mono text-xs sm:text-sm text-text-muted border border-border-soft rounded-lg px-4 py-2.5 bg-surface/50"
                  >
                    "{p}"
                  </div>
                ))}
              </div>
            </div>
          </div>

          <DepartureBoard />
        </div>
      </section>

      {/* How it thinks */}
      <section id="how-it-thinks" className="max-w-6xl mx-auto px-6 py-24">
        <p className="label-eyebrow mb-3">How it thinks</p>
        <h2 className="font-display text-3xl sm:text-4xl text-text mb-14 max-w-2xl">
          Five agents, one conversation, and a critic that isn't afraid to send it back.
        </h2>

        <div className="grid md:grid-cols-5 gap-px bg-border rounded-2xl overflow-hidden border border-border">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage.label} className="bg-bg-soft p-6 flex flex-col gap-3">
              <span className="font-mono text-xs text-accent">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="font-display text-xl text-text">{stage.label}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{stage.detail}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-24 border-t border-border grid md:grid-cols-3 gap-10">
        <Feature
          title="Every claim is priced"
          body="Flights, hotels, activities, food, transit -- broken into a real budget, compared against yours, and trimmed automatically when it runs over."
        />
        <Feature
          title="You can talk back"
          body='"Hotels are too expensive." "Remove the museums." "Change Tokyo to Kyoto." Say it in plain language -- only the affected part of the plan reruns.'
        />
        <Feature
          title="Runs without a single paid key"
          body="A full demo mode with realistic mock flights, hotels, and places, clearly labeled, so you can see the whole system work before connecting anything real."
        />
      </section>

      <section className="border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="font-display text-3xl sm:text-4xl text-text mb-6">
            Describe the trip. Watch it get planned.
          </h2>
          <Link
            to={user ? "/trips/new" : "/register"}
            className="inline-block px-8 py-3.5 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors"
          >
            Start planning
          </Link>
        </div>
      </section>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h3 className="font-display text-xl text-text mb-2">{title}</h3>
      <p className="text-sm text-text-muted leading-relaxed">{body}</p>
    </div>
  );
}
