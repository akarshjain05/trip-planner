import type { Activity, ItineraryDay } from "../types";

const ACTIVITY_ICON: Record<Activity["activity_type"], string> = {
  flight: "\u2708",
  transfer: "\uD83D\uDE95",
  meal: "\uD83C\uDF7D",
  attraction: "\uD83D\uDCCD",
  hotel_checkin: "\uD83D\uDECC",
  hotel_checkout: "\uD83C\uDFE8",
  free_time: "\u2600",
  other: "\u2022",
};

function formatCurrency(amount: number | null, currency: string): string {
  if (amount === null || amount === 0) return "";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

export function ItineraryDayCard({ day, currency }: { day: ItineraryDay; currency: string }) {
  return (
    <div className="ticket-card px-8 py-6">
      <div className="flex items-baseline justify-between mb-1 flex-wrap gap-x-4 gap-y-1">
        <h3 className="font-display text-xl text-paper-ink">{day.title ?? `Day ${day.day_number}`}</h3>
        {day.weather_summary && (
          <span className="font-mono text-xs text-paper-ink/60">{day.weather_summary}</span>
        )}
      </div>
      {day.date && (
        <p className="font-mono text-[11px] text-paper-ink/50 mb-4 tracking-wide">{day.date}</p>
      )}

      <div className="flex flex-col divide-y divide-paper-ink/10 mt-4">
        {day.activities.map((activity) => (
          <div key={activity.id} className="flex items-start gap-3 py-2.5">
            <span className="font-mono text-xs text-paper-ink/50 w-12 shrink-0 pt-0.5">
              {activity.time ?? ""}
            </span>
            <span className="shrink-0" aria-hidden>{ACTIVITY_ICON[activity.activity_type]}</span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-paper-ink font-medium">{activity.title}</p>
              {activity.description && (
                <p className="text-xs text-paper-ink/60 mt-0.5 leading-relaxed">{activity.description}</p>
              )}
            </div>
            {activity.estimated_cost != null && activity.estimated_cost > 0 && (
              <span className="font-mono text-xs text-paper-ink/70 shrink-0">
                {formatCurrency(activity.estimated_cost, currency)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
