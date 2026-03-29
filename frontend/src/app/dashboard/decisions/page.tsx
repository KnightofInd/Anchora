"use client";

import { useState, FormEvent, useDeferredValue, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { decisionsApi, workflowApi, getApiErrorMessage } from "@/lib/api";
import { EmptyState, ErrorState, LoadingState } from "@/app/dashboard/_components/query-states";
import { useToast } from "@/app/_components/toast";

interface Decision {
  id: string;
  title: string;
  description: string | null;
  context: string | null;
  status: string;
  confidence_score: number | null;
  risk_score: number | null;
  reasoning_summary: string | null;
  created_at: string;
}

interface DecisionDetail extends Decision {
  updated_at?: string;
  assumptions?: string[];
  meeting_notes?: MeetingNote[];
  references?: Array<{
    id: string;
    document_id: string | null;
    data_source: string | null;
    reference_type: string;
  }>;
}

interface MeetingNote {
  id: string;
  decision_id: string;
  meeting_title: string | null;
  transcript_text: string;
  execution_guidance: string | null;
  action_items: string[];
  created_at: string;
  updated_at: string;
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
  if (score < 5) return { label: `Low (${score.toFixed(1)})`, color: "bg-green-500" };
  if (score < 8) return { label: `Med (${score.toFixed(1)})`, color: "bg-amber-400" };
  return { label: `High (${score.toFixed(1)})`, color: "bg-red-500" };
}

export default function DecisionsPage() {
  const PAGE_SIZE = 8;
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [showModal, setShowModal] = useState(false);
  const [form, setForm]           = useState({ title: "", description: "", context: "" });
  const [formError, setFormError] = useState("");
  const [filterTab, setFilterTab] = useState("");
  const [search, setSearch]       = useState("");
  const [page, setPage] = useState(1);
  const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(null);
  const [meetingForm, setMeetingForm] = useState({
    meeting_title: "",
    transcript_text: "",
    execution_guidance: "",
    action_items: "",
  });
  const [meetingFormError, setMeetingFormError] = useState("");
  const deferredSearch = useDeferredValue(search);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["decisions", filterTab, page],
    queryFn: () =>
      decisionsApi.list({
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
        ...(filterTab ? { status: filterTab } : {}),
      }),
  });

  const createMutation = useMutation({
    mutationFn: () => decisionsApi.create(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["decisions"] });
      setShowModal(false);
      setForm({ title: "", description: "", context: "" });
      setFormError("");
      showToast({
        variant: "success",
        title: "Decision created",
        message: "Your decision entered the governance pipeline.",
      });
    },
    onError: (err: unknown) => {
      const message = getApiErrorMessage(err, "Failed to create decision.");
      setFormError(message);
      showToast({ variant: "error", title: "Create failed", message });
    },
  });

  const startWorkflowMutation = useMutation({
    mutationFn: (decision_id: string) => workflowApi.start(decision_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      showToast({
        variant: "success",
        title: "Workflow started",
        message: "Approval steps were generated successfully.",
      });
    },
    onError: (err: unknown) => {
      showToast({
        variant: "error",
        title: "Workflow start failed",
        message: getApiErrorMessage(err, "Unable to start workflow."),
      });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      decisionsApi.updateStatus(id, status),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["decisions"] });
      showToast({
        variant: "success",
        title: "Decision updated",
        message: `Status changed to ${variables.status}.`,
      });
    },
    onError: (err: unknown) => {
      showToast({
        variant: "error",
        title: "Status update failed",
        message: getApiErrorMessage(err, "Unable to update status."),
      });
    },
  });

  const createMeetingNoteMutation = useMutation({
    mutationFn: () => {
      if (!selectedDecisionId) {
        throw new Error("No decision selected.");
      }
      const actionItems = meetingForm.action_items
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
      return decisionsApi.createMeetingNote(selectedDecisionId, {
        meeting_title: meetingForm.meeting_title.trim() || undefined,
        transcript_text: meetingForm.transcript_text.trim(),
        execution_guidance: meetingForm.execution_guidance.trim() || undefined,
        action_items: actionItems,
      });
    },
    onSuccess: () => {
      if (selectedDecisionId) {
        qc.invalidateQueries({ queryKey: ["decision", selectedDecisionId] });
      }
      setMeetingForm({ meeting_title: "", transcript_text: "", execution_guidance: "", action_items: "" });
      setMeetingFormError("");
      showToast({
        variant: "success",
        title: "Meeting note added",
        message: "Transcript and execution guidance saved.",
      });
    },
    onError: (err: unknown) => {
      const message = getApiErrorMessage(err, "Failed to save meeting note.");
      setMeetingFormError(message);
      showToast({ variant: "error", title: "Save failed", message });
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.context.length < 10) { setFormError("Context must be at least 10 characters."); return; }
    createMutation.mutate();
  }

  function handleMeetingNoteSubmit(e: FormEvent) {
    e.preventDefault();
    if (meetingForm.transcript_text.trim().length < 20) {
      setMeetingFormError("Transcript must be at least 20 characters.");
      return;
    }
    createMeetingNoteMutation.mutate();
  }

  const pageItems = useMemo<Decision[]>(() => data?.data ?? [], [data]);
  const {
    data: selectedDecisionResponse,
    isLoading: isDecisionDetailLoading,
    isError: isDecisionDetailError,
    error: decisionDetailError,
    refetch: refetchDecisionDetail,
  } = useQuery({
    queryKey: ["decision", selectedDecisionId],
    queryFn: () => decisionsApi.get(selectedDecisionId as string),
    enabled: Boolean(selectedDecisionId),
  });
  const selectedDecision = selectedDecisionResponse?.data as DecisionDetail | undefined;
  useEffect(() => {
    setMeetingForm({ meeting_title: "", transcript_text: "", execution_guidance: "", action_items: "" });
    setMeetingFormError("");
  }, [selectedDecisionId]);
  const filtered = useMemo(
    () =>
      pageItems.filter((d) => {
        const q = deferredSearch.trim().toLowerCase();
        const matchSearch = q
          ? d.title.toLowerCase().includes(q) || (d.description ?? "").toLowerCase().includes(q)
          : true;
        return matchSearch;
      }),
    [pageItems, deferredSearch]
  );
  const hasNextPage = pageItems.length === PAGE_SIZE;

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
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search decisions…"
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae]/30"
          />
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {FILTER_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => {
                setFilterTab(key);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filterTab === key
                  ? "bg-[#1e3fae] text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-4">
            <LoadingState label="Loading decisions..." />
          </div>
        ) : isError ? (
          <div className="p-4">
            <ErrorState
              title="Could not load decisions"
              message={getApiErrorMessage(error, "Failed to load decisions.")}
              onRetry={() => {
                void refetch();
              }}
            />
          </div>
        ) : !filtered.length ? (
          <div className="p-4">
            <EmptyState
              icon="balance"
              title="No decisions found"
              description={search || filterTab ? "Try changing your filters or search text." : "Create your first decision to begin the governance workflow."}
            />
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
                    <tr
                      key={d.id}
                      className="hover:bg-slate-50 group cursor-pointer"
                      onClick={() => setSelectedDecisionId(d.id)}
                    >
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
                        {d.reasoning_summary ? (
                          <div className="bg-[#1e3fae]/5 border-l-[3px] border-[#1e3fae] px-3 py-2 rounded-r-lg">
                            <p className="text-[12px] text-slate-600 italic line-clamp-2 leading-relaxed">{d.reasoning_summary}</p>
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
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateStatusMutation.mutate({ id: d.id, status: "approved" });
                                }}
                                disabled={updateStatusMutation.isPending}
                                title="Approve decision"
                                className="p-1.5 rounded-lg bg-green-50 hover:bg-green-100 text-green-600 transition-colors disabled:opacity-50"
                              >
                                <span className="material-symbols-outlined text-[14px] leading-none">check_circle</span>
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  updateStatusMutation.mutate({ id: d.id, status: "rejected" });
                                }}
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
                              onClick={(e) => {
                                e.stopPropagation();
                                updateStatusMutation.mutate({ id: d.id, status: "executed" });
                              }}
                              disabled={updateStatusMutation.isPending}
                              title="Execute decision"
                              className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-600 transition-colors disabled:opacity-50"
                            >
                              <span className="material-symbols-outlined text-[14px] leading-none">play_circle</span>
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              startWorkflowMutation.mutate(d.id);
                            }}
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
            <p className="text-xs text-slate-400">
              Showing page {page} ({filtered.length} result{filtered.length !== 1 ? "s" : ""})
            </p>
            <div className="flex items-center gap-1">
              <button
                className="p-1 rounded hover:bg-slate-100 text-slate-400 disabled:opacity-30"
                disabled={page <= 1}
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              >
                <span className="material-symbols-outlined text-sm">chevron_left</span>
              </button>
              <span className="px-2 py-0.5 rounded bg-[#1e3fae] text-white text-xs font-semibold">{page}</span>
              <button
                className="p-1 rounded hover:bg-slate-100 text-slate-400 disabled:opacity-30"
                disabled={!hasNextPage}
                onClick={() => setPage((prev) => prev + 1)}
              >
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

      {selectedDecisionId && (
        <div className="fixed inset-0 z-[65] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-[760px] bg-white rounded-2xl shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Decision Review</h2>
                <p className="text-xs text-slate-500 mt-0.5">Review original request details before workflow actions.</p>
              </div>
              <button
                onClick={() => setSelectedDecisionId(null)}
                className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              {isDecisionDetailLoading ? (
                <LoadingState label="Loading decision details..." />
              ) : isDecisionDetailError ? (
                <ErrorState
                  title="Could not load decision details"
                  message={getApiErrorMessage(decisionDetailError, "Failed to load decision details.")}
                  onRetry={() => {
                    void refetchDecisionDetail();
                  }}
                />
              ) : !selectedDecision ? (
                <EmptyState
                  icon="info"
                  title="Decision not found"
                  description="This decision may have been removed or is no longer accessible."
                />
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Title</p>
                      <p className="text-sm text-slate-900 mt-1">{selectedDecision.title}</p>
                    </div>
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</p>
                      <p className="text-sm text-slate-900 mt-1 capitalize">{selectedDecision.status}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Confidence Score</p>
                      <p className="text-sm text-slate-900 mt-1">
                        {selectedDecision.confidence_score == null
                          ? "Not available"
                          : `${Math.round(selectedDecision.confidence_score * 100)}% (${selectedDecision.confidence_score.toFixed(2)})`}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk Score</p>
                      <p className="text-sm text-slate-900 mt-1">
                        {selectedDecision.risk_score == null ? "Not available" : selectedDecision.risk_score.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</p>
                    <p className="text-sm text-slate-800 mt-1 whitespace-pre-wrap">{selectedDecision.description || "No description provided."}</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Original Context (Submitted Input)</p>
                    <p className="text-sm text-slate-800 mt-1 whitespace-pre-wrap">{selectedDecision.context || "Context not available for this historical decision."}</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4 space-y-4">
                    <div>
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Meeting Transcript and Execution Guidance</p>
                      <p className="text-xs text-slate-500 mt-1">Capture meeting discussion, execution remarks, and follow-up action items for team alignment.</p>
                    </div>

                    <form onSubmit={handleMeetingNoteSubmit} className="space-y-3">
                      {meetingFormError && (
                        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                          {meetingFormError}
                        </div>
                      )}

                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Meeting Title</label>
                        <input
                          value={meetingForm.meeting_title}
                          onChange={(e) => setMeetingForm((prev) => ({ ...prev, meeting_title: e.target.value }))}
                          placeholder="e.g. Weekly execution sync - Region rollout"
                          className="w-full h-10 px-3 rounded-lg border border-slate-300 text-sm"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Meeting Transcript</label>
                        <textarea
                          required
                          rows={4}
                          value={meetingForm.transcript_text}
                          onChange={(e) => setMeetingForm((prev) => ({ ...prev, transcript_text: e.target.value }))}
                          placeholder="Paste the meeting transcript or discussion summary..."
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm resize-y"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Execution Guidance / Remarks</label>
                        <textarea
                          rows={3}
                          value={meetingForm.execution_guidance}
                          onChange={(e) => setMeetingForm((prev) => ({ ...prev, execution_guidance: e.target.value }))}
                          placeholder="Add practical guidance the team should follow during execution..."
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm resize-y"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Action Items (one per line)</label>
                        <textarea
                          rows={3}
                          value={meetingForm.action_items}
                          onChange={(e) => setMeetingForm((prev) => ({ ...prev, action_items: e.target.value }))}
                          placeholder="Owner to verify legal checklist\nOps to prepare rollout plan"
                          className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm resize-y"
                        />
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={createMeetingNoteMutation.isPending}
                          className="h-9 px-4 rounded-lg bg-[#1e3fae] text-white text-sm font-semibold disabled:opacity-60"
                        >
                          {createMeetingNoteMutation.isPending ? "Saving..." : "Add Meeting Note"}
                        </button>
                      </div>
                    </form>

                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Saved Meeting Notes</p>
                      {selectedDecision.meeting_notes && selectedDecision.meeting_notes.length > 0 ? (
                        <div className="space-y-2">
                          {selectedDecision.meeting_notes.map((note) => (
                            <div key={note.id} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 space-y-2">
                              <div className="flex items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-slate-800">{note.meeting_title || "Untitled meeting note"}</p>
                                <span className="text-[11px] text-slate-500">{new Date(note.created_at).toLocaleString()}</span>
                              </div>
                              <div>
                                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Transcript</p>
                                <p className="text-sm text-slate-700 whitespace-pre-wrap mt-1">{note.transcript_text}</p>
                              </div>
                              <div>
                                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Guidance</p>
                                <p className="text-sm text-slate-700 whitespace-pre-wrap mt-1">{note.execution_guidance || "No additional guidance."}</p>
                              </div>
                              <div>
                                <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Action Items</p>
                                {note.action_items && note.action_items.length > 0 ? (
                                  <ul className="list-disc pl-5 mt-1 space-y-1">
                                    {note.action_items.map((item, index) => (
                                      <li key={`${note.id}-item-${index}`} className="text-sm text-slate-700">{item}</li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-sm text-slate-500 mt-1">No action items.</p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500">No meeting notes added yet.</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-[#1e3fae]/20 bg-[#1e3fae]/5 p-4">
                    <p className="text-xs font-semibold text-[#1e3fae] uppercase tracking-wide">AI Reasoning Summary</p>
                    <p className="text-sm text-slate-800 mt-1 whitespace-pre-wrap">{selectedDecision.reasoning_summary || "No AI reasoning available."}</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">AI Assumptions</p>
                    {selectedDecision.assumptions && selectedDecision.assumptions.length > 0 ? (
                      <ul className="mt-2 list-disc pl-5 space-y-1">
                        {selectedDecision.assumptions.map((assumption, index) => (
                          <li key={`${selectedDecision.id}-assumption-${index}`} className="text-sm text-slate-800">
                            {assumption}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-500 mt-1">No assumptions recorded.</p>
                    )}
                  </div>

                  <div className="rounded-xl border border-slate-200 p-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">References</p>
                    {selectedDecision.references && selectedDecision.references.length > 0 ? (
                      <div className="mt-2 space-y-2">
                        {selectedDecision.references.map((reference) => (
                          <div key={reference.id} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                            <p className="text-xs text-slate-700">
                              <span className="font-semibold">Type:</span> {reference.reference_type}
                            </p>
                            <p className="text-xs text-slate-700 mt-0.5">
                              <span className="font-semibold">Document ID:</span> {reference.document_id ?? "N/A"}
                            </p>
                            <p className="text-xs text-slate-700 mt-0.5">
                              <span className="font-semibold">Source:</span> {reference.data_source ?? "N/A"}
                            </p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-500 mt-1">No references attached.</p>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Created At</p>
                      <p className="text-sm text-slate-900 mt-1">
                        {selectedDecision.created_at
                          ? new Date(selectedDecision.created_at).toLocaleString()
                          : "Not available"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-200 p-4">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Updated At</p>
                      <p className="text-sm text-slate-900 mt-1">
                        {selectedDecision.updated_at
                          ? new Date(selectedDecision.updated_at).toLocaleString()
                          : "Not available"}
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


