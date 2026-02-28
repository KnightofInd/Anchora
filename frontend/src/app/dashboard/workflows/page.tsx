"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workflowApi } from "@/lib/api";

interface Task {
  id: string;
  name: string;
  status: string;
  assigned_role: string | null;
  completed_by: string | null;
  completed_at: string | null;
  approval_notes: Record<string, string | number | boolean> | null;
}

interface Workflow {
  id: string;
  decision_id: string;
  status: string;
  created_at: string;
  tasks: Task[];
}

const WF_STATUS: Record<string, { pill: string; dot: string; label: string }> = {
  pending:   { pill: "bg-amber-100 text-amber-700",   dot: "bg-amber-400",   label: "Pending" },
  in_review: { pill: "bg-blue-100 text-blue-700",     dot: "bg-blue-500",    label: "In Review" },
  approved:  { pill: "bg-green-100 text-green-700",   dot: "bg-green-500",   label: "Approved" },
  rejected:  { pill: "bg-red-100 text-red-700",       dot: "bg-red-500",     label: "Rejected" },
  completed: { pill: "bg-teal-100 text-teal-700",     dot: "bg-teal-500",    label: "Completed" },
};

const TABS = [
  { key: "",          label: "All Workflows" },
  { key: "pending",   label: "Pending My Action" },
  { key: "completed", label: "Completed" },
  { key: "rejected",  label: "Rejected" },
];

function roleInitials(role: string | undefined | null) {
  if (!role) return "?";
  return role.split(/[\s_]+/).map((w) => w[0]?.toUpperCase() ?? "").slice(0, 2).join("");
}

function relTime(ts: string) {
  const diff = Math.round((Date.now() - new Date(ts).getTime()) / 60000);
  if (diff < 1)    return "just now";
  if (diff < 60)   return `${diff}m ago`;
  if (diff < 1440) return `${Math.round(diff / 60)}h ago`;
  return `${Math.round(diff / 1440)}d ago`;
}

export default function WorkflowsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn:  () => workflowApi.list(),
  });

  const approveMutation = useMutation({
    mutationFn: ({ workflow_id, task_id }: { workflow_id: string; task_id: string }) =>
      workflowApi.approveTask(workflow_id, task_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ workflow_id, task_id }: { workflow_id: string; task_id: string }) =>
      workflowApi.rejectTask(workflow_id, task_id, "Rejected by reviewer"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
  });

  const allWf: Workflow[] = data?.data ?? [];
  const filtered = tab ? allWf.filter((w) => w.status === tab) : allWf;

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-slate-900">Workflow Monitor</h1>
          <p className="text-sm text-slate-500 mt-0.5">Track multi-step approval workflows for each decision.</p>
        </div>
        <button className="flex items-center gap-1.5 h-9 px-4 rounded-xl border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 text-sm font-medium transition-colors shadow-sm">
          <span className="material-symbols-outlined text-base leading-none">tune</span>
          Filter
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {TABS.map(({ key, label }) => {
          const count = key ? allWf.filter((w) => w.status === key).length : allWf.length;
          return (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                tab === key
                  ? "bg-[#1e3fae] text-white shadow-sm"
                  : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {label}
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${tab === key ? "bg-white/20 text-white" : "bg-slate-100 text-slate-500"}`}>
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Cards */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400 text-sm shadow-sm">Loading…</div>
      ) : !filtered.length ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center shadow-sm">
          <span className="material-symbols-outlined text-3xl text-slate-300">account_tree</span>
          <p className="text-slate-400 text-sm mt-2">No workflows found. Start one from the Decisions page.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((wf) => {
            const wfSc = WF_STATUS[wf.status] ?? WF_STATUS.pending;
            const pendingTask = wf.tasks?.find((t) => t.status === "pending");
            const rejectedTask = wf.tasks?.find((t) => t.status === "rejected");

            return (
              <div key={wf.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden relative">
                {/* Status badge absolute */}
                <span className={`absolute top-4 right-4 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${wfSc.pill}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${wfSc.dot}`} />
                  {wfSc.label}
                </span>

                <div className="px-6 pt-5 pb-4 pr-28">
                  {/* WF ID + title */}
                  <p className="text-[11px] font-mono text-slate-400 tracking-wide">WF-{wf.id.slice(0, 8).toUpperCase()}</p>
                  <p className="text-[15px] font-bold text-slate-900 mt-0.5">
                    Workflow for Decision{" "}
                    <span className="font-mono text-slate-500 text-[13px]">{wf.decision_id.slice(0, 8)}…</span>
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">Initiated · {relTime(wf.created_at)}</p>
                </div>

                {/* Stepper */}
                {wf.tasks?.length > 0 && (
                  <div className="px-6 pb-4">
                    <div className="flex items-center gap-0">
                      {wf.tasks.map((task, idx) => {
                        const isDone = task.status === "completed" || task.status === "approved";
                        const isCurrent = task.status === "pending";
                        const isRejected = task.status === "rejected";
                        const isLast = idx === wf.tasks.length - 1;

                        const circleClass = isDone
                          ? "bg-green-100 text-green-700"
                          : isRejected
                          ? "bg-red-100 text-red-700"
                          : isCurrent
                          ? "bg-[#1e3fae] text-white ring-4 ring-[#1e3fae]/20"
                          : "bg-slate-100 text-slate-400";

                        const lineClass = isDone ? "bg-green-300" : isCurrent ? "bg-[#1e3fae]/30" : "bg-slate-100";

                        return (
                          <div key={task.id} className="flex items-center">
                            <div className="flex flex-col items-center gap-1">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 transition-all ${circleClass}`}>
                                {isRejected ? (
                                  <span className="material-symbols-outlined text-sm leading-none">close</span>
                                ) : isDone ? (
                                  <span className="material-symbols-outlined text-sm leading-none">check</span>
                                ) : (
                                  roleInitials((task.approval_notes as Record<string, string>)?.role)
                                )}
                              </div>
                              <p className="text-[10px] text-slate-400 text-center w-16 truncate">{(task.approval_notes as Record<string, string>)?.role ?? "—"}</p>
                            </div>
                            {!isLast && (
                              <div className={`h-0.5 w-8 mx-1 mb-5 rounded ${lineClass}`} />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Action row */}
                {pendingTask && (
                  <div className="mx-5 mb-5 rounded-xl bg-slate-50 px-4 py-3 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="material-symbols-outlined text-amber-500 text-sm">schedule</span>
                      Waiting for <span className="font-semibold text-slate-700">{pendingTask.assigned_role}</span> approval
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => approveMutation.mutate({ workflow_id: wf.id, task_id: pendingTask.id })}
                        disabled={approveMutation.isPending || rejectMutation.isPending}
                        className="h-8 px-4 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-semibold shadow-sm transition-colors disabled:opacity-50"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => rejectMutation.mutate({ workflow_id: wf.id, task_id: pendingTask.id })}
                        disabled={approveMutation.isPending || rejectMutation.isPending}
                        className="h-8 px-4 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}

                {rejectedTask && !pendingTask && (
                  <div className="mx-5 mb-5 rounded-xl bg-red-50 border border-red-100 px-4 py-3 flex items-start gap-2">
                    <span className="material-symbols-outlined text-red-500 text-sm mt-0.5 shrink-0">warning</span>
                    <div>
                      <p className="text-xs font-semibold text-red-700">Workflow Rejected</p>
                      <p className="text-[11px] text-red-500 mt-0.5">Rejected at step: {rejectedTask.assigned_role}</p>
                    </div>
                  </div>
                )}

                {wf.status === "completed" && (
                  <div className="mx-5 mb-5 rounded-xl bg-green-50 border border-green-100 px-4 py-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-green-600 text-sm shrink-0">check_circle</span>
                    <p className="text-xs font-semibold text-green-700">All steps completed successfully.</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination hint */}
      {filtered.length > 0 && (
        <div className="flex items-center justify-between pt-1">
          <p className="text-xs text-slate-400">Showing {filtered.length} of {allWf.length} workflows</p>
          <div className="flex items-center gap-1">
            <button className="p-1.5 rounded-lg hover:bg-white border border-slate-200 text-slate-400 disabled:opacity-30" disabled>
              <span className="material-symbols-outlined text-sm">chevron_left</span>
            </button>
            <span className="px-2.5 py-1 rounded-lg bg-[#1e3fae] text-white text-xs font-semibold">1</span>
            <button className="p-1.5 rounded-lg hover:bg-white border border-slate-200 text-slate-400 disabled:opacity-30" disabled>
              <span className="material-symbols-outlined text-sm">chevron_right</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
