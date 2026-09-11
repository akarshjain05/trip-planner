import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { Budget } from "../types";

const CATEGORY_LABEL: Record<string, string> = {
  flights: "Flights",
  hotels: "Hotels",
  local_transport: "Local transport",
  intercity_transport: "Intercity transport",
  food: "Food",
  activities: "Activities",
  shopping_allowance: "Shopping",
  emergency_buffer: "Buffer",
  taxes_fees: "Taxes & fees",
};

const COLORS = ["#C9A24B", "#4B9C8C", "#7DBFB1", "#E2C583", "#9098B8", "#616A94", "#B4483A", "#363F6E", "#232B52"];

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

export function BudgetChart({ budget }: { budget: Budget }) {
  const data = budget.lines
    .filter((l) => l.estimated_amount > 0)
    .map((l) => ({ name: CATEGORY_LABEL[l.category] ?? l.category, value: l.estimated_amount }));

  const overBudget = budget.total_budget != null && budget.total_estimated > budget.total_budget;

  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-6">
      <p className="label-eyebrow mb-4">Budget</p>

      <div className="grid sm:grid-cols-2 gap-6 items-center">
        <div className="h-48" role="figure" aria-label="Budget breakdown pie chart">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2}>
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />
                ))}
              </Pie>
              <Tooltip
                formatter={(v) => formatCurrency(Number(v ?? 0), budget.currency)}
                contentStyle={{ background: "#1B2140", border: "1px solid #2A3158", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#EDE8D8" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div>
          <dl className="flex flex-col gap-2 mb-4">
            <Row label="Estimated total" value={formatCurrency(budget.total_estimated, budget.currency)} />
            {budget.total_budget != null && (
              <>
                <Row label="Your budget" value={formatCurrency(budget.total_budget, budget.currency)} />
                <Row
                  label={overBudget ? "Over by" : "Remaining"}
                  value={formatCurrency(Math.abs(budget.remaining ?? 0), budget.currency)}
                  accent={overBudget ? "stamp" : "jade"}
                />
              </>
            )}
          </dl>
          <div className="flex flex-col gap-1.5">
            {data.map((d, i) => (
              <div key={d.name} className="flex items-center gap-2 text-xs">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                <span className="text-text-muted">{d.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: "jade" | "stamp" }) {
  const color = accent === "jade" ? "text-jade" : accent === "stamp" ? "text-stamp" : "text-text";
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={`font-mono text-sm ${color}`}>{value}</span>
    </div>
  );
}
