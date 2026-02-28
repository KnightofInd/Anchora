"use client";

import { useState, FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { decisionsApi, workflowApi } from "@/lib/api";

interface Decision {
  id: string;
  title: string;
  description: string | null;
  status: string;
  confidence_score: number | null;
  risk_score: number | null;
  ai_reasoning: string | null;
  created_at: string;
}

/* ── Status config ── */
const STATUS_MAP: Record<string, { pill: string; dot: string; label: string }> = {
  draft:     { pill: "bg-slate-100 text-slate-600",   dot: "bg-slate-400",   label: "Draft" },
  approved:  { pill: "bg-green-100 text-green-700",   dot: "bg-green-500",   label: "Approved" },
  rejected:  { pill: "bg-red-100 text-red-700",       dot: "bg-red-500",     label: "Rejected" },
  executed:  { pill: "bg-blue-100 text-blue-700",     dot: "bg-blue-500",    label: "Executed" },
  pending:   { pill: "bg-amber-100 text-amber-700",   dot: "bg-amber-400",   label: "Pending" },
  in_review: { pill: "bg-purple-100 text-purple-700", dot: "bg-purple-500",  label: "In Review" },
  completed: { pill: "bg-teal-100 text-teal-700",     dot: "bg-teal-500",    label: "Completed" },
};

const FILTER_TABS = [
  { key: "", label: "All Decisions" },
  { key: "pending",   label: "Pending" },
  { key: "draft",     label: "Draft" },
  { key: "approved",  label: "Approved" },
  { key: "rejected",  label: "Rejected" },
];

function riskLabel(score: number | null) {
  if (score == null) return { label: "—", color: "bg-slate-300" };
  if (score < 0.35) return { label: `Low (${Math.round(score * 100)})`, color: "bg-green-500" };
  if (score < 0.65) return { label: `Med (${Math.round(score * 100)})`, color: "bg-amber-400" };
  return { label: `High (${Math.round(score * 100)})`, color: "bg-red-500" };
}

export default function DecisionsPage() {
  const qc = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm]           = useState({ title: "", description: "", context: "" });
  const [formError, setFormError] = useState("");
  const [filterTab, setFilterTab] = useState("");
  const [search, setSearch]       = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["decisions"],
    queryFn: () => decisionsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => decisionsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["decisions"] });
      setShowModal(false);
      setForm({ title: "", description: "", context: "" });
      setFormError("");
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Failed to create decision.";
      setFormError(typeof msg === "string" ? msg : JSON.stringify(msg));
    },
  });

  const startWorkflowMutation = useMutation({
    mutationFn: (decision_id: string) => workflowApi.start(decision_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      decisionsApi.updateStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["decisions"] }),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.context.length < 10) { setFormError("Context must be at least 10 characters."); return; }
    createMutation.mutate();
  }

  const all: Decision[] = data?.data ?? [];
  const filtered = all.filter((d) => {
    const matchTab = filterTab ? d.status === filterTab : true;
    const matchSearch = search ? d.title.toLowerCase().includes(search.toLowerCase()) : true;
    return matchTab && matchSearch;
  });

  const pendingCount = all.filter((d) => d.status === "pending").length;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Decision Pipeline</h1>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[11px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-0.5">All decisions are first-class objects with full AI traceability.</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 h-9 px-4 rounded-xl bg-[#1e3fae] hover:bg-[#162f85] text-white text-sm font-semibold shadow-sm shadow-[#1e3fae]/20 transition-colors"
        >
          <span className="material-symbols-outlined text-base leading-none">add</span>
          New Decision
        </button>
      </div>

      {/* Filter bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 flex items-center gap-3 flex-wrap shadow-sm">
        <div className="relative flex-1 min-w-[160px]">
          <span className="material-symbols-outlined text-slate-400 text-base absolute left-3 top-1/2 -translate-y-1/2">search</span>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search decisions…"
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae]/30"
          />
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {FILTER_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilterTab(key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === key
                  ? "bg-[#1e3fae] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {label}
              {key === "pending" && pendingCount > 0 && (
                <span className="ml-1 text-[10px]">[{pendingCount}]</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Loading decisions…</div>
        ) : !filtered.length ? (
          <div className="p-8 text-center">
            <span className="material-symbols-outlined text-3xl text-slate-300">balance</span>
            <p className="text-slate-400 text-sm mt-2">No decisions found.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead className="border-b border-slate-100 bg-slate-50 text-left">
                <tr>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Decision</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Status</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Confidence</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Risk</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">AI Reasoning</th>
                  <th className="px-5 py-3 text-xs font-semibold text-slate-400 uppercase tracking-wide">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filtered.map((d) => {
                  const sc   = STATUS_MAP[d.status] ?? STATUS_MAP.draft;
                  const conf = d.confidence_score != null ? Math.round(d.confidence_score * 100) : null;
                  const risk = riskLabel(d.risk_score);
                  const confColor = conf == null ? "bg-slate-200" : conf >= 70 ? "bg-green-500" : conf >= 40 ? "bg-amber-400" : "bg-red-400";
                  return (
                    <tr key={d.id} className="hover:bg-slate-50 group">
                      {/* Title */}
                      <td className="px-5 py-4 max-w-[220px]">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <p className="font-semibold text-slate-900 text-[13px] truncate max-w-[160px]">{d.title}</p>
                              <span className="inline-flex text-[10px] font-bold px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700 shrink-0">AI</span>
                            </div>
                            <p className="text-[11px] text-slate-400 font-mono mt-0.5">{d.id.slice(0, 8)}…</p>
                          </div>
                        </div>
                      </td>
                      {/* Status */}
                      <td className="px-5 py-4">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${sc.pill}`}>
                          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${sc.dot}`} />
                          {sc.label}
                        </span>
                      </td>
                      {/* Confidence */}
                      <td className="px-5 py-4">
                        {conf != null ? (
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden shrink-0">
                              <div className={`h-full rounded-full ${confColor}`} style={{ width: `${conf}%` }} />
                            </div>
                            <span className="text-xs font-semibold text-slate-700">{conf}%</span>
                          </div>
                        ) : <span className="text-slate-300 text-xs">—</span>}
                      </td>
                      {/* Risk */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5">
                          <span className={`w-2 h-2 rounded-full shrink-0 ${risk.color}`} />
                          <span className="text-xs text-slate-600 whitespace-nowrap">{risk.label}</span>
                        </div>
                      </td>
                      {/* AI Reasoning */}
                      <td className="px-5 py-4 max-w-[260px]">
                        {d.ai_reasoning ? (
                          <div className="bg-[#1e3fae]/5 border-l-[3px] border-[#1e3fae] px-3 py-2 rounded-r-lg">
                            <p className="text-[12px] text-slate-600 italic line-clamp-2 leading-relaxed">{d.ai_reasoning}</p>
                          </div>
                        ) : (
                          <span className="text-slate-300 text-xs">No reasoning yet</span>
                        )}
                      </td>
                      {/* Actions */}
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {d.status === "draft" && (
                            <>
                              <button
                                onClick={() => updateStatusMutation.mutate({ id: d.id, status: "approved" })}
                                disabled={updateStatusMutation.isPending}
                                title="Approve decision"
                                className="p-1.5 rounded-lg bg-green-50 hover:bg-green-100 text-green-600 transition-colors disabled:opacity-50"
                              >
                                <span className="material-symbols-outlined text-[14px] leading-none">check_circle</span>
                              </button>
                              <button
                                onClick={() => updateStatusMutation.mutate({ id: d.id, status: "rejected" })}
                                disabled={updateStatusMutation.isPending}
                                title="Reject decision"
                                className="p-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-500 transition-colors disabled:opacity-50"
                              >
                                <span className="material-symbols-outlined text-[14px] leading-none">cancel</span>
                              </button>
                            </>
                          )}
                          {d.status === "approved" && (
                            <button
                              onClick={() => updateStatusMutation.mutate({ id: d.id, status: "executed" })}
                              disabled={updateStatusMutation.isPending}
                              title="Execute decision"
                              className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 transition-colors disabled:opacity-50"
                            >
                              <span className="material-symbols-outlined text-[14px] leading-none">play_circle</span>
                            </button>
                          )}
                          <button
                            onClick={() => startWorkflowMutation.mutate(d.id)}
                            disabled={startWorkflowMutation.isPending}
                            title="Start workflow"
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-[#1e3fae]/10 text-slate-500 hover:text-[#1e3fae] transition-colors disabled:opacity-50"
                          >
                            <span className="material-symbols-outlined text-[14px] leading-none">account_tree</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {/* Pagination hint */}
        {filtered.length > 0 && (
          <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between">
            <p className="text-xs text-slate-400">Showing {filtered.length} of {all.length} decisions</p>
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

      {/* ── Create Decision Modal ── */}
      {showModal && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-[560px] bg-white rounded-2xl shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
              <h2 className="text-lg font-bold text-slate-900">New Decision</h2>
              <button
                onClick={() => { setShowModal(false); setFormError(""); }}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* Body */}
            <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
              {formError && (
                <div className="flex items-center gap-2 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  <span className="material-symbols-outlined text-base shrink-0">error</span>
                  {formError}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Title <span className="text-red-500">*</span></label>
                <input
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="e.g. Approve new vendor contract"
                  className="w-full h-11 px-3 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae] focus:border-transparent transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Description</label>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Optional brief description"
                  className="w-full h-11 px-3 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae] focus:border-transparent transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">
                  Context / Background <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <textarea
                    required
                    value={form.context}
                    onChange={(e) => setForm({ ...form, context: e.target.value })}
                    rows={5}
                    maxLength={2000}
                    placeholder="Provide the full business context for the AI engine to analyse…"
                    className="w-full px-3 pt-3 pb-8 rounded-xl border border-slate-300 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae] focus:border-transparent transition-all resize-none"
                  />
                  <div className="absolute bottom-2 right-3 flex items-center gap-1 text-[10px] text-slate-400">
                    <span className="material-symbols-outlined text-[12px]">auto_awesome</span>
                    <span>{form.context.length}/2000 chars</span>
                  </div>
                </div>
              </div>

              {/* AI banner */}
              <div className="flex items-start gap-3 rounded-xl bg-[#1e3fae]/5 border border-[#1e3fae]/10 px-4 py-3">
                <span className="material-symbols-outlined text-[#1e3fae] text-xl shrink-0 mt-0.5">smart_toy</span>
                <div>
                  <p className="text-[13px] font-semibold text-slate-800">AI Reasoning Engine</p>
                  <p className="text-[12px] text-slate-500 mt-0.5 leading-relaxed">Our AI will analyse the context and generate a confidence score, risk assessment, and reasoning rationale to support the governance process.</p>
                </div>
              </div>

              {/* Footer */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setFormError(""); }}
                  className="h-10 px-5 rounded-xl border border-slate-200 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="h-10 px-5 rounded-xl bg-[#1e3fae] hover:bg-[#162f85] text-white text-sm font-semibold shadow-md shadow-[#1e3fae]/20 flex items-center gap-1.5 transition-colors disabled:opacity-60"
                >
                  {createMutation.isPending ? (
                    <>
                      <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                      </svg>
                      Creating…
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-base leading-none">add</span>
                      Create Decision
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}


