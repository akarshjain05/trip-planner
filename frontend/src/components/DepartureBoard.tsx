import { useEffect, useState } from "react";

interface Row {
  agent: string;
  status: "boarding" | "departed" | "on time" | "delayed";
}

const SEQUENCES: Row[][] = [
  [
    { agent: "REQUIREMENTS", status: "departed" },
    { agent: "DESTINATION", status: "boarding" },
    { agent: "FLIGHTS", status: "on time" },
    { agent: "HOTELS", status: "on time" },
    { agent: "CRITIC", status: "on time" },
  ],
  [
    { agent: "REQUIREMENTS", status: "departed" },
    { agent: "DESTINATION", status: "departed" },
    { agent: "FLIGHTS", status: "boarding" },
    { agent: "HOTELS", status: "boarding" },
    { agent: "CRITIC", status: "on time" },
  ],
  [
    { agent: "REQUIREMENTS", status: "departed" },
    { agent: "DESTINATION", status: "departed" },
    { agent: "FLIGHTS", status: "departed" },
    { agent: "HOTELS", status: "departed" },
    { agent: "CRITIC", status: "boarding" },
  ],
  [
    { agent: "REQUIREMENTS", status: "departed" },
    { agent: "DESTINATION", status: "departed" },
    { agent: "BUDGET", status: "delayed" },
    { agent: "HOTELS", status: "departed" },
    { agent: "CRITIC", status: "departed" },
  ],
];

const STATUS_COLOR: Record<Row["status"], string> = {
  boarding: "text-accent",
  "on time": "text-text-faint",
  departed: "text-jade",
  delayed: "text-stamp",
};

export function DepartureBoard() {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % SEQUENCES.length), 2200);
    return () => clearInterval(t);
  }, []);

  const rows = SEQUENCES[idx] ?? SEQUENCES[0]!;

  return (
    <div className="rounded-2xl border border-border-soft bg-surface p-5 shadow-2xl shadow-black/40">
      <div className="flex items-center justify-between mb-4 px-1">
        <span className="label-eyebrow">Agent execution</span>
        <span className="font-mono text-[10px] text-text-faint">LIVE · TRIP #JP-08</span>
      </div>
      <div className="rounded-lg bg-bg border border-border overflow-hidden">
        <div className="grid grid-cols-[1fr_auto] gap-x-4 px-4 py-2.5 border-b border-border">
          <span className="font-mono text-[10px] text-text-faint tracking-widest">AGENT</span>
          <span className="font-mono text-[10px] text-text-faint tracking-widest">STATUS</span>
        </div>
        {rows.map((row) => (
          <div
            key={row.agent}
            className="grid grid-cols-[1fr_auto] gap-x-4 px-4 py-3 border-b border-border last:border-b-0 transition-colors duration-500"
          >
            <span className="font-mono text-sm text-text tracking-wide">{row.agent}</span>
            <span className={`font-mono text-sm tracking-wide uppercase ${STATUS_COLOR[row.status]}`}>
              {row.status}
            </span>
          </div>
        ))}
      </div>
      <p className="text-[11px] text-text-faint mt-3 px-1 font-mono">
        a preview -- your real trip streams here live
      </p>
    </div>
  );
}
