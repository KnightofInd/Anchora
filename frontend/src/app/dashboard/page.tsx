"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { decisionsApi, workflowApi, auditApi } from "@/lib/api";

/* ── helpers ── */
function riskLabel(score: number | null) {
  if (score == null) return { label: "—", color: "bg-slate-300" };
  if (score < 0.35) return { label: "Low", color: "bg-green-500" };
  if (score < 0.65) return { label: "Med", color: "bg-amber-400" };
  return { label: "High", color: "bg-red-500" };
}

const STATUS_COLORS: Record<string, { pill: string; dot: string }> = {
  draft:     { pill: "bg-slate-100 text-slate-600",   dot: "bg-slate-400" },
  approved:  { pill: "bg-green-100 text-green-700",   dot: "bg-green-500" },
  rejected:  { pill: "bg-red-100 text-red-700",       dot: "bg-red-500" },
  executed:  { pill: "bg-blue-100 text-blue-700",     dot: "bg-blue-500" },
  pending:   { pill: "bg-amber-100 text-amber-700",   dot: "bg-amber-400" },
  in_review: { pill: "bg-purple-100 text-purple-700", dot: "bg-purple-500" },
  completed: { pill: "bg-teal-100 text-teal-700",     dot: "bg-teal-500" },
};

const ICON_COLORS = [
  { icon: "analytics",      bg: "bg-[#1e3fae]/10", fg: "text-[#1e3fae]" },
  { icon: "pending",        bg: "bg-amber-50",      fg: "text-amber-600" },
  { icon: "check_circle",   bg: "bg-green-50",      fg: "text-green-600" },
  { icon: "policy",         bg: "bg-purple-50",     fg: "text-purple-600" },
];

const ENTITY_ICONS: Record<string, { icon: string; bg: string; fg: string }> = {
  decision: { icon: "balance",       bg: "bg-blue-100",   fg: "text-blue-700" },
  workflow: { icon: "account_tree",  bg: "bg-purple-100", fg: "text-purple-700" },
  task:     { icon: "task_alt",      bg: "bg-teal-100",   fg: "text-teal-700" },
  document: { icon: "description",   bg: "bg-amber-100",  fg: "text-amber-700" },
  user:     { icon: "person",        bg: "bg-slate-100",  fg: "text-slate-600" },
};

export default function DashboardPage() {
  const decisions = useQuery({ queryKey: ["decisions"], queryFn: () => decisionsApi.list() });
  const workflows = useQuery({ queryKey: ["workflows"], queryFn: () => workflowApi.list() });
  const auditLogs = useQuery({ queryKey: ["audit"],     queryFn: () => auditApi.list() });

  const decList = decisions.data?.data ?? [];
  const wfList  = workflows.data?.data ?? [];
  const auList  = auditLogs.data?.data ?? [];

  const totalDecisions = decList.length;
  const pendingWorkflows = wfList.filter((w: { status: string }) => w.status === "pending").length;
  const complianceRate = (() => {
    if (!decList.length) return 0;
    const passing = decList.filter(
      (d: { confidence_score: number | null }) =>
        d.confidence_score != null && d.confidence_score >= 0.5
    ).length;
    return Math.round((passing / decList.length) * 100);
  })();
  const auditCount = auList.length;

  const stats = [
    { label: "Total Decisions",    value: String(totalDecisions),        trend: "+12%",       trendColor: "bg-green-100 text-green-700", loading: decisions.isLoading, ...ICON_COLORS[0] },
    { label: "Pending Workflows",  value: String(pendingWorkflows),      trend: "+2 Today",   trendColor: "bg-amber-100 text-amber-700",  loading: workflows.isLoading, ...ICON_COLORS[1] },
    { label: "Compliance Rate",    value: `${complianceRate}%`,          trend: "+0.4%",      trendColor: "bg-green-100 text-green-700",  loading: decisions.isLoading, ...ICON_COLORS[2] },
    { label: "Audit Events",       value: String(auditCount),            trend: "Daily",      trendColor: "bg-slate-100 text-slate-600",  loading: auditLogs.isLoading, ...ICON_COLORS[3] },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Governance Overview</h1>
        <p className="text-sm text-slate-500 mt-0.5">Decision Intelligence &amp; Compliance Platform</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, trend, trendColor, loading, icon, bg, fg }) => (
          <div key={label} className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div className={`p-2 rounded-xl ${bg}`}>
                <span className={`material-symbols-outlined text-xl leading-none ${fg}`}>{icon}</span>
              </div>
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${trendColor}`}>{trend}</span>
            </div>
            <div>
              <p className="text-xs text-slate-500 font-medium">{label}</p>
              {loading
                ? <div className="mt-1 h-7 w-14 animate-pulse rounded bg-slate-100" />
                : <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
              }
            </div>
          </div>
        ))}
      </div>

      {/* Main two-column grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-6">
        {/* Recent decisions table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 className="text-[15px] font-semibold text-slate-800">Recent Decisions</h2>
            <Link href="/dashboard/decisions" className="text-xs font-medium text-[#1e3fae] hover:underline">View all</Link>
          </div>
          {decisions.isLoading ? (
            <div className="p-6 text-center text-slate-400 text-sm">Loading…</div>
          ) : !decList.length ? (
            <div className="p-6 text-center text-slate-400 text-sm">No decisions yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50 text-left">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Decision</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Status</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Confidence</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Risk</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {decList.slice(0, 6).map((d: {
                  id: string; title: string; status: string;
                  confidence_score: number | null; risk_score: number | null; created_at: string;
                }) => {
                  const sc = STATUS_COLORS[d.status] ?? STATUS_COLORS.draft;
                  const conf = d.confidence_score != null ? Math.round(d.confidence_score * 100) : null;
                  const risk = riskLabel(d.risk_score);
                  return (
                    <tr key={d.id} className="hover:bg-slate-50 group">
                      <td className="px-6 py-3.5">
                        <p className="font-semibold text-slate-900 text-[13px] truncate max-w-[200px]">{d.title}</p>
                        <p className="text-[11px] text-slate-400 font-mono mt-0.5">{d.id.slice(0, 8)}…</p>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${sc.pill}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${sc.dot}`} />
                          {d.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        {conf != null ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden shrink-0">
                              <div className="h-full bg-[#1e3fae] rounded-full" style={{ width: `${conf}%` }} />
                            </div>
                            <span className="text-xs text-slate-600 font-medium">{conf}%</span>
                          </div>
                        ) : <span className="text-slate-300">—</span>}
                      </td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${risk.color}`} />
                          <span className="text-xs text-slate-600">{risk.label}</span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-xs text-slate-400">
                        {new Date(d.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Activity feed */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h2 className="text-[15px] font-semibold text-slate-800">Recent Activity</h2>
            <Link href="/dashboard/audit" className="text-xs font-medium text-[#1e3fae] hover:underline">View log</Link>
          </div>
          <div className="divide-y divide-slate-50 overflow-y-auto max-h-[420px]">
            {auditLogs.isLoading ? (
              <div className="p-5 text-center text-slate-400 text-sm">Loading…</div>
            ) : !auList.length ? (
              <div className="p-5 text-center text-slate-400 text-sm">No activity yet.</div>
            ) : (
              auList.slice(0, 10).map((log: {
                id: string; entity_type: string; action: string;
                performed_by: string; timestamp: string;
              }) => {
                const meta = ENTITY_ICONS[log.entity_type] ?? { icon: "info", bg: "bg-slate-100", fg: "text-slate-600" };
                const when = new Date(log.timestamp);
                const diff = Math.round((Date.now() - when.getTime()) / 60000);
                const relTime = diff < 1 ? "just now" : diff < 60 ? `${diff}m ago` : diff < 1440 ? `${Math.round(diff / 60)}h ago` : `${Math.round(diff / 1440)}d ago`;
                return (
                  <div key={log.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-slate-50">
                    <div className={`p-1.5 rounded-lg shrink-0 mt-0.5 ${meta.bg}`}>
                      <span className={`material-symbols-outlined text-[14px] leading-none ${meta.fg}`}>{meta.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-800 truncate">{log.action.replace(/_/g, " ")}</p>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">{log.performed_by}</p>
                    </div>
                    <span className="text-[10px] text-slate-400 whitespace-nowrap mt-0.5 shrink-0">{relTime}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


