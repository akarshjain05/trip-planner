import { useQuery } from "@tanstack/react-query";
import { fetchAdminStats } from "../services/api";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export function AdminDashboardPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["admin-stats"], queryFn: fetchAdminStats });

  if (isLoading) {
    return <div className="max-w-5xl mx-auto px-6 py-16 text-text-muted">Loading dashboard...</div>;
  }

  if (error || !data) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-16">
        <h1 className="text-2xl text-stamp mb-4">Access Denied</h1>
        <p className="text-text-muted">You do not have permission to view the admin dashboard.</p>
      </div>
    );
  }

  const { aggregate, recent_runs } = data;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }} 
      animate={{ opacity: 1, y: 0 }} 
      className="max-w-5xl mx-auto px-6 py-16"
    >
      <p className="label-eyebrow mb-2">Admin Dashboard</p>
      <h1 className="font-display text-3xl text-text mb-10">System Observability</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-6 mb-12">
        <StatCard title="Total Agent Runs" value={aggregate.total_runs} />
        <StatCard title="Input Tokens" value={aggregate.total_input_tokens.toLocaleString()} />
        <StatCard title="Output Tokens" value={aggregate.total_output_tokens.toLocaleString()} />
        <StatCard title="Est. LLM Cost" value={`$${aggregate.total_cost_usd.toFixed(4)}`} />
        <StatCard title="Total Iterations" value={aggregate.total_iterations} />
        <StatCard title="Tool Calls" value={aggregate.total_tool_calls} />
      </div>

      <h2 className="font-display text-2xl text-text mb-6">Recent Agent Runs</h2>
      <div className="bg-surface border border-border-soft rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-bg text-text-muted border-b border-border font-mono text-[10px] tracking-widest uppercase">
            <tr>
              <th className="px-5 py-3 font-medium">Time</th>
              <th className="px-5 py-3 font-medium">Trip</th>
              <th className="px-5 py-3 font-medium">Status</th>
              <th className="px-5 py-3 font-medium">Trigger</th>
              <th className="px-5 py-3 font-medium text-right">Iters</th>
              <th className="px-5 py-3 font-medium text-right">Tools</th>
              <th className="px-5 py-3 font-medium text-right">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-soft text-text">
            {recent_runs.map((r: any) => (
              <tr key={r.id} className="hover:bg-bg/50 transition-colors">
                <td className="px-5 py-3 font-mono text-xs text-text-faint">
                  {new Date(r.created_at).toLocaleString()}
                </td>
                <td className="px-5 py-3">
                  <Link to={`/trips/${r.trip_id}`} className="text-accent hover:underline">
                    View Trip
                  </Link>
                </td>
                <td className="px-5 py-3">
                  <span className={`px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider ${
                    r.status === 'completed' ? 'bg-jade/20 text-jade' :
                    r.status === 'failed' ? 'bg-stamp/20 text-stamp' :
                    'bg-accent/20 text-accent'
                  }`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-5 py-3 font-mono text-xs">{r.trigger}</td>
                <td className="px-5 py-3 text-right font-mono text-xs">{r.iteration_count}</td>
                <td className="px-5 py-3 text-right font-mono text-xs">{r.tool_call_count}</td>
                <td className="px-5 py-3 text-right font-mono text-xs">${r.estimated_cost_usd.toFixed(4)}</td>
              </tr>
            ))}
            {recent_runs.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-text-muted">No agent runs found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

function StatCard({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="border border-border-soft rounded-xl bg-surface p-5 flex flex-col justify-center">
      <p className="font-mono text-[10px] uppercase tracking-widest text-text-faint mb-2">{title}</p>
      <p className="font-display text-3xl text-text">{value}</p>
    </div>
  );
}
