# ANCHORA

## *Decision Intelligence & Governance Operating System*

---

> **The future of enterprise decision-making isn't faster. It's traceable, intelligent, and provably compliant.**

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    ◆  SYSTEM ONLINE  ◆                            │
│                                                                   │
│    Decision Intelligence Engine v0.1.0                           │
│    Status: Operational  |  Auth: Verified  |  Audit: Immutable   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## What This Is

Anchora is not a workflow tool. It is not a simple approval system.

**Anchora is a decision operating system** — a cryptographically-grounded, AI-augmented, governance-enforced platform where every decision is:

- **Traceable**: Full audit chain from input to execution
- **Intelligent**: AI reasoning + risk scoring + confidence quantification  
- **Governed**: Policy engine + compliance gates + breach detection
- **Immutable**: Append-only audit logs with temporal proof
- **Enterprise-Ready**: RBAC, JWT rotation, SLO monitoring, semantic retrieval

Every decision object is a first-class citizen. Every transition is logged. Every reasoning is preserved.

---

## The Philosophy

In legacy enterprise systems, decisions disappear into email threads and spreadsheets. Governance becomes forensics.

Anchora inverts this:

| Legacy | Anchora |
|--------|---------|
| Decisions scattered across channels | Decisions are structured, queryable objects |
| Governance applied retroactively | Governance enforced in real-time |
| Risk is guessed | Risk is quantified and scored |
| Audit trails are reconstructed | Audit is immutable, native, complete |

The result: organizations make **faster decisions** with **more confidence**, not less.

---

## Core Capabilities

### Intelligent Reasoning Engine
Every decision is reasoned by Gemini 1.5-pro, grounded in your knowledge base through semantic retrieval. Confidence and risk are quantified, not guessed. Assumptions are extracted and audited.

### Real-Time Policy Enforcement
Policy engine evaluates decisions *before* they enter workflows. Violations trigger automatic escalation. Rules are versioned and frozen at decision time — future policy changes don't retroactively alter compliance.

### Risk-Aware Workflows
Multi-step task chains adapt to risk level. Low-risk decisions skip approval. High-risk decisions escalate through analyst → manager → compliance. Every task transition is logged with full context.

### Semantic Knowledge Retrieval
Upload documents once. They're automatically embedded (768-dim pgvector). Every decision retrieves relevant context. AI reasoning is grounded in *your* data — not hallucinations.

### Quality Observability
Every decision captures grounding score, retrieval metadata, model provenance, and policy snapshots. Reproducibility is built in.

### Immutable Audit Trail
Full lifecycle traceability: decision created → compliance checked → workflow started → tasks approved/rejected. Database-enforced append-only logs. No deletion. No tampering.

### SLO-Driven Operations
Real-time metrics: error rate, p95 latency, compliance violations. Operational health dashboard. Governance isn't just correct — it's fast.

---

## System Architecture

### **The Layered Operating System**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│             Next.js 14 | React 19 | Tailwind CSS               │
│  Dashboard • Decisions • Workflows • Knowledge • Audit Viewer   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                        │
│  /auth  |  /decisions  |  /workflows  |  /knowledge  |  /audit  │
└─────────────────────────────────────────────────────────────────┘
                              ▲
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  INTELLIGENCE │  │   GOVERNANCE     │  │   PERSISTENCE   │
│  Google LLM   │  │ Policy Evaluator │  │  PostgreSQL +   │
│  Embeddings   │  │ Compliance Check │  │  pgvector       │
│  Reasoning    │  │ Risk Scoring     │  │  Audit Logs     │
└───────────────┘  └──────────────────┘  └──────────────────┘
```

### **Service Architecture**

```
Authentication           Policy Engine              Knowledge System
├─ JWT Generation        ├─ Policy Evaluation       ├─ Document Upload
├─ Refresh Rotation      ├─ Risk Assessment        ├─ Embedding Gen
├─ Session Management    ├─ Compliance Check       ├─ Semantic Search
└─ JTI Blocklist         └─ Escalation Logic       └─ Retrieval Cache

    ▼                          ▼                        ▼
    
Decision Pipeline            Workflow Pipeline         Audit Pipeline
├─ Create Decision      →     ├─ Start Workflow   →    ├─ Event Log
├─ AI Reasoning               ├─ Task Generation       ├─ State Trail
├─ Grounding Check            ├─ Approval Chain        ├─ User Trail
├─ Policy Check               ├─ Rejection Handler     └─ Immutable
└─ Persist (Audit)            └─ Completion Handler        Chain
```

---

## The Decision Engine Pipeline

Every decision flows through a proven, automated pipeline designed for speed and governance:

```
REQUEST
│ title, description, context
│
▼
┌─────────────────────────────────────────────┐
│  SEMANTIC RETRIEVAL                         │
│  • Query embedding (Gemini)                 │
│  • pgvector cosine search                   │
│  • Fallback to recent documents             │
└──────────────┬────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  AI REASONING ENGINE (Gemini 1.5-pro)       │
│  • Generate reasoning_summary               │
│  • Compute confidence_score (0.0-1.0)      │
│  • Compute risk_score (0.0-10.0)           │
│  • Extract assumptions + evidence           │
└──────────────┬────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  GROUNDING QUALITY GATE                     │
│  • Citation coverage analysis               │
│  • Lexical overlap scoring                  │
│  • Weighted quality metric                  │
│  • BLOCK if score < threshold              │
└──────────────┬────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  POLICY ENGINE (Pre-Check)                  │
│  • Evaluate all active policies             │
│  • Risk-aware escalation                    │
│  • Compliance gates                         │
│  • BLOCK if violations exist               │
└──────────────┬────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  PERSIST DECISION                           │
│  • Store with policy snapshot               │
│  • Link to retrieved documents              │
│  • Audit log event                          │
│  • Idempotency guard                        │
└──────────────┬────────────────────────────┘
               │
               ▼
          ✓ CREATED (DRAFT)
```

---

## Technology Stack

### Backend & Core

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI | Modern async Python web |
| **Database** | PostgreSQL (Supabase) | Primary store + audit logs |
| **Vector DB** | pgvector | Semantic similarity search |
| **Storage** | Supabase Storage | Document storage + signed URLs |
| **ORM** | SQLAlchemy 2.0 | Async database access |
| **Migrations** | Alembic | SQL versioning & schema management |

### AI & Intelligence

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM** | Google Gemini 1.5-pro | Decision reasoning + analysis |
| **Embeddings** | Gemini embedding-001 | 768-dim semantic vectors |
| **Grounding Evaluator** | Custom Python | Citation scoring + quality gates |
| **Retrieval** | pgvector cosine | Fast semantic search |

### Frontend & Experience

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Next.js 14 (React 19) | App router + server components |
| **State Mgmt** | TanStack React Query v5 | Async data + cache |
| **Styling** | Tailwind CSS 3.4 | Utility-first design system |
| **Forms** | React Hook Form + Zod | Type-safe form validation |
| **HTTP** | Axios | API requests + interceptors |
| **UI State** | Custom Providers | Toast notifications + session |

### Infrastructure & DevOps

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Containerization** | Docker + docker-compose | Local dev + staging |
| **Frontend Deploy** | Vercel | Optimized React hosting |
| **Backend Deploy** | Cloud Run / Heroku | Serverless Python |
| **CI/CD** | GitHub Actions | Lint, type-check, test, deploy |
| **Monitoring** | Request metrics | SLO tracking + observability |

### Security & Compliance

| Feature | Implementation | Purpose |
|---------|--------------|---------|
| **Auth** | JWT (HS256) + Refresh | Stateless, scalable auth |
| **Password** | bcrypt | Secure hashing |
| **Cookies** | HttpOnly + Secure + SameSite | XSS + CSRF protection |
| **Token Reuse** | JTI tracking | Prevent token replay |
| **Idempotency** | Request dedup | Prevent duplicate submissions |
| **Audit** | Append-only PostgreSQL | Immutable governance trail |
| **RBAC** | Role-based access control | Endpoint-level authorization |

---

## Getting Started

### Prerequisites

```
Python 3.10+
Node.js 18+
PostgreSQL 13+ (or Supabase cloud)
Google AI API key (Gemini access)
```

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with DATABASE_URL, GEMINI_API_KEY, SUPABASE credentials

# Initialize database
alembic upgrade head
python seed.py

# Run backend
uvicorn app.main:app --reload
# API at http://localhost:8000/api/docs
```

### Frontend Setup

```bash
cd frontend
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000/api

npm run dev
# Frontend at http://localhost:3000
```

### Docker Compose (Quickstart)

```bash
docker-compose up
# API at http://localhost:8000/api
# Frontend at http://localhost:3000
# DB at localhost:5432
```

### Production Deployment

**Backend:**
```bash
export DATABASE_URL=postgresql://...
export GEMINI_API_KEY=...
export SECRET_KEY=$(openssl rand -hex 32)
export AUTH_COOKIE_SECURE=true

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
vercel --prod
# Set NEXT_PUBLIC_API_URL to production backend
```

---

## Example: Making a Decision

### Via REST API

```bash
curl -X POST http://localhost:8000/api/decisions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: req-12345" \
  -d '{
    "title": "Approve vendor contract for cloud services",
    "description": "5-year managed Kubernetes agreement",
    "context": "Current: on-prem. Target: cloud migration. Risk: downtime. Budget: $2.5M/year"
  }'
```

**Response (201 CREATED):**
```json
{
  "id": "dec_abc123",
  "title": "Approve vendor contract for cloud services",
  "status": "draft",
  "confidence_score": 0.78,
  "risk_score": 6.2,
  "ai_reasoning": "Based on operational requirements and budget alignment, recommend approval with contingency planning for downtime mitigation.",
  "policy_snapshot": {
    "rules_evaluated": [...],
    "violations": []
  },
  "quality_snapshot": {
    "grounding": {
      "score": 0.85,
      "citation_coverage": 0.9,
      "lexical_overlap": 0.78
    },
    "retrieval": {
      "mode": "semantic",
      "document_count": 3
    },
    "model": "gemini-1.5-pro-001"
  }
}
```

### Via Dashboard

1. Navigate to `/dashboard/decisions`
2. Click **New Decision**
3. Enter title + context
4. Submit → AI reasons → Risk assessed → Policy checked → Stored
5. View full traceability
6. Approve or start workflow

---

## Security & Trust Model

### Authentication & Session Management

- **JWT Tokens**: 30-minute access tokens with refresh rotation
- **Refresh Tokens**: Rotated on every refresh, tracked via JTI
- **Cookie Security**: HttpOnly + Secure + SameSite=Lax
- **Brute-Force Protection**: 5 failed logins → 15-minute lockout
- **Session Expiry**: Automatic on inactivity

### Authorization & Access Control

- **Role-Based Access Control (RBAC)**: Admin, Analyst, Manager, Auditor, Viewer
- **Endpoint Protection**: Every route enforced with role checks
- **Decision Ownership**: Users can only view/edit their own decisions (unless admin)
- **Workflow Assignment**: Managers approve assigned tasks only

### Audit & Immutability

- **Append-Only Logs**: Database-enforced immutability (no UPDATEs to audit table)
- **Event Logging**: Every action tracked: `decision.created`, `task.approved`, `policy.violated`
- **Lifecycle Traceability**: Full path from input → output via `/audit/trace/{decision_id}`
- **Policy Snapshots**: Policies frozen at decision time (no retroactive compliance changes)
- **Timestamps**: UTC, auditable, synchronized

### Data Integrity & Protection

- **Idempotency Keys**: Prevent duplicate submissions via `Idempotency-Key` header
- **Document Integrity**: SHA-256 hashing for uploaded files
- **Token Reuse Detection**: Cryptographic JTI tracking
- **Row-Level Locking**: Prevents race conditions on task approvals
- **Encrypted Secrets**: GEMINI_API_KEY never logged, only used server-side

### Governance Enforcement

- **Pre-Creation Policies**: Violations block decision creation (not post-hoc)
- **Automated Escalation**: High-risk decisions → compliance review
- **Grounding Quality Gate**: AI reasoning must cite sources (>70% threshold)
- **Compliance Audit**: Non-fatal checks logged for reporting

---

## Roadmap: Strategic Evolution

### Phase 5 — Foundation ✓
- Complete core decision + workflow engine
- Immutable audit trail
- Semantic knowledge retrieval
- Real-time policy enforcement
- Dashboard & API fundamentals

### Phase 6 — Integration Layer *In Progress*
- ERP/CRM adapters (decision push-back)
- Advanced policy engine (OPA integration)
- Batch operations (bulk decisions + approvals)
- Custom LLM support (beyond Gemini)
- Advanced analytics dashboard

### Phase 7 — Enterprise Scale *Planned*
- Multi-tenant support (data isolation)
- Compliance reporting (SOC 2, ISO 27001, GDPR)
- Webhook integrations (real-time notifications)
- Mobile app (iOS/Android approvals)
- White-label platform

### Phase 8 — Ecosystem *Envisioned*
- Third-party integrations marketplace
- Custom policy language (DSL)
- Decision analytics + ML insights
- GraphQL API
- Blockchain audit trail option

---

## Contributing

Anchora welcomes builders, operators, and thinkers who believe in intelligent governance.

### Development Workflow

```bash
# 1. Fork & clone
git clone https://github.com/nexacore/anchora.git
cd anchora

# 2. Create feature branch
git checkout -b feature/your-feature

# 3. Implement with tests
# Backend: pytest tests/
# Frontend: npm run lint

# 4. Run checks
cd backend && pytest tests/ -v
cd frontend && npm run lint && npm run build

# 5. Submit PR
git push origin feature/your-feature
# Open pull request with clear description
```

### Code Standards

**Backend (Python)**
- Type hints on all functions
- Docstrings for public APIs
- Async/await patterns for I/O
- Tests for critical paths
- Conventional commits (feat:, fix:, docs:)

**Frontend (TypeScript)**
- TypeScript strict mode
- React Query conventions
- Tailwind component patterns
- Unit tests for logic
- E2E tests for workflows

### Areas for Contribution

- Policy engine enhancements (OPA)
- LLM backend integrations (LLaMA, Mistral, GPT-4)
- Dashboard visualizations (decision trends, risk heatmaps)
- Mobile app scaffolding
- Deployment automation (Terraform, Helm)
- Documentation + tutorials
- Compliance framework tooling

---

## Documentation

- **[Agent Transfer Guide](./AGENT_TRANSFER_GUIDE.md)** — Technical handoff for developers
- **[API Reference](./backend/docs/api.md)** — Complete endpoint specifications
- **[Database Schema](./backend/docs/schema.md)** — Entity relationships & indexing
- **[Security Model](./backend/docs/security.md)** — Auth, RBAC, audit architecture
- **[Deployment Guide](./backend/docs/deployment.md)** — Production setup & scaling

---

## License

Anchora is licensed under the **Apache 2.0 License**.

See [LICENSE](./LICENSE) for details.

---

## Support & Community

| Channel | Purpose |
|---------|---------|
| **GitHub Issues** | Bugs, feature requests, technical discussions |
| **GitHub Discussions** | Architecture questions, RFCs, ideas |
| **Email** | contact@nexacore.dev |
| **Security** | security@nexacore.dev (responsible disclosure) |

---

```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│   ╔═══════════════════════════════════════════════════════╗   │
│   ║                                                       ║   │
│   ║   ANCHORA: Where Intelligence Meets Governance       ║   │
│   ║                                                       ║   │
│   ║   Every decision leaves a trace.                     ║   │
│   ║   Every trace tells the truth.                       ║   │
│   ║   Every truth builds trust.                          ║   │
│   ║                                                       ║   │
│   ║   Build with conviction.                             ║   │
│   ║   Decide with confidence.                            ║   │
│   ║   Govern with transparency.                          ║   │
│   ║                                                       ║   │
│   ╚═══════════════════════════════════════════════════════╝   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

---

**Last Updated**: May 2026 | **Version**: 0.1.0 | **Status**: Operational | **License**: Apache 2.0
