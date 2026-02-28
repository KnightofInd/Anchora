"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { auditApi } from "@/lib/api";

interface AuditLog {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  performed_by: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

const ENTITY_CONFIG: Record<string, { icon: string; bg: string; fg: string; label: string }> = {
  decision: { icon: "balance",      bg: "bg-blue-100",   fg: "text-blue-700",   label: "Decision" },
  workflow: { icon: "account_tree", bg: "bg-purple-100", fg: "text-purple-700", label: "Workflow" },
  task:     { icon: "task_alt",     bg: "bg-teal-100",   fg: "text-teal-700",   label: "Task" },
  document: { icon: "description",  bg: "bg-amber-100",  fg: "text-amber-700",  label: "Document" },
  user:     { icon: "person",       bg: "bg-slate-100",  fg: "text-slate-600",  label: "User" },
};

const FILTER_CHIPS = [
  { key: "",         label: "All" },
  { key: "decision", label: "Decisions" },
  { key: "workflow", label: "Workflows" },
  { key: "user",     label: "Users" },
  { key: "document", label: "Documents" },
  { key: "task",     label: "Tasks" },
];

function performerInitials(name: string) {
  return name.replace(/@.*/, "").split(/[\s._-]+/).map((w) => w[0]?.toUpperCase() ?? "").slice(0, 2).join("") || "?";
}

export default function AuditPage() {
  const [entityFilter, setEntityFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["audit", entityFilter],
    queryFn: () => auditApi.list(entityFilter ? { entity_type: entityFilter } : {}),
  });

  const logs: AuditLog[] = data?.data ?? [];

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Immutable Audit Log</h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[11px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">Append-only record of every action in the system.</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button className="flex items-center gap-1.5 h-9 px-4 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors shadow-sm">
            <span className="material-symbols-outlined text-base leading-none">download</span>
            Export CSV
          </button>
          <button className="flex items-center gap-1.5 h-9 px-4 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors shadow-sm">
            <span className="material-symbols-outlined text-base leading-none">verified</span>
            Verify Chain
          </button>
        </div>
      </div>

      {/* Filter chips */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4 flex items-center gap-2 flex-wrap">
        <span className="text-xs font-semibold text-slate-400 mr-1">Filter by:</span>
        {FILTER_CHIPS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setEntityFilter(key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
              entityFilter === key
                ? "bg-[#1e3fae] text-white shadow-sm"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {key && (
              <span className={`material-symbols-outlined text-[12px] leading-none ${entityFilter === key ? "text-white" : (ENTITY_CONFIG[key]?.fg ?? "text-slate-500")}`}>
                {ENTITY_CONFIG[key]?.icon ?? "label"}
              </span>
            )}
            {label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading audit events…</div>
        ) : !logs.length ? (
          <div className="p-8 text-center">
            <span className="material-symbols-outlined text-3xl text-slate-300">description</span>
            <p className="text-slate-400 text-sm mt-2">No audit events found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[760px]">
              <thead className="border-b border-slate-100 bg-slate-50 text-left">
                <tr>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Timestamp</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Entity Type</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Action</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Entity ID</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Performed By</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {logs.map((log) => {
                  const ec = ENTITY_CONFIG[log.entity_type] ?? { icon: "label", bg: "bg-slate-100", fg: "text-slate-600", label: log.entity_type };
                  return (
                    <tr key={log.id} className="hover:bg-slate-50 group">
                      {/* Timestamp */}
                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span className="font-mono text-[11px] text-slate-500">
                          {new Date(log.timestamp).toISOString().replace("T", " ").slice(0, 19)}
                        </span>
                      </td>
                      {/* Entity type badge */}
                      <td className="px-5 py-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold ${ec.bg} ${ec.fg}`}>
                          <span className={`material-symbols-outlined text-[12px] leading-none ${ec.fg}`}>{ec.icon}</span>
                          {ec.label}
                        </span>
                      </td>
                      {/* Action */}
                      <td className="px-5 py-3.5">
                        <span className="text-[13px] font-bold text-slate-800">{log.action.replace(/_/g, " ")}</span>
                      </td>
                      {/* Entity ID */}
                      <td className="px-5 py-3.5">
                        <code className="text-[11px] font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 text-slate-600">
                          {log.entity_id.slice(0, 12)}…
                        </code>
                      </td>
                      {/* Performed by */}
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-[#1e3fae]/10 flex items-center justify-center text-[#1e3fae] text-[9px] font-bold shrink-0">
                            {performerInitials(log.performed_by)}
                          </div>
                          <span className="text-xs text-slate-600 truncate max-w-[140px]">{log.performed_by}</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {logs.length > 0 && (
          <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
            <p className="text-xs text-slate-400">Showing {logs.length} results</p>
            <div className="flex items-center gap-1">
              <button className="p-1 rounded hover:bg-slate-100 text-slate-400 disabled:opacity-30" disabled>
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <span className="px-2 py-0.5 rounded bg-[#1e3fae] text-white text-xs font-semibold">1</span>
              <button className="p-1 rounded hover:bg-slate-100 text-slate-400 disabled:opacity-30" disabled>
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
