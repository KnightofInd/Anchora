import { z } from "zod";

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

// ─── Decision ─────────────────────────────────────────────────────────────────
export const decisionCreateSchema = z.object({
  title: z.string().min(3).max(512),
  description: z.string().optional(),
  context: z.string().min(10, "Context must be at least 10 characters"),
});

export type DecisionCreateForm = z.infer<typeof decisionCreateSchema>;

// ─── Decision (API response) ──────────────────────────────────────────────────
export const decisionSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  description: z.string().nullable(),
  reasoning_summary: z.string().nullable(),
  confidence_score: z.number().nullable(),
  risk_score: z.number().nullable(),
  assumptions: z.array(z.string()),
  status: z.enum(["draft", "approved", "rejected", "executed"]),
  created_by: z.string().uuid(),
  created_at: z.string(),
  references: z.array(z.object({
    id: z.string(),
    document_id: z.string().nullable(),
    reference_type: z.string(),
    data_source: z.string().nullable(),
  })),
});

export type Decision = z.infer<typeof decisionSchema>;

// ─── Audit ───────────────────────────────────────────────────────────────────
export const auditLogSchema = z.object({
  id: z.string(),
  entity_type: z.string(),
  entity_id: z.string(),
  action: z.string(),
  performed_by: z.string(),
  timestamp: z.string(),
  metadata: z.record(z.unknown()),
});

export type AuditLog = z.infer<typeof auditLogSchema>;
