# HUCE-KMS — Global AI Coding Agent Guidelines

> **Project**: HUCE-KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Scope**: Entire Monorepo (`apps/backend`, `apps/web`, `docs`)  
> **Last Updated**: 2026-11-08  
> **Target Audience**: Mandatory guidelines for all AI Coding Agents inspecting, analyzing, and developing code in this repository.

---

## 1. Project Overview

HUCE-KMS is an academic knowledge management platform, regulatory repository, and intelligent AI assistant serving faculty, staff, and students at Hanoi University of Civil Engineering (HUCE).

The repository is structured as an **isolated monorepo** with independent Frontend and Backend workspaces:

```text
huce-kms/
├── apps/
│   ├── backend/          # Backend API (Python 3.12, FastAPI, SQLAlchemy 2.0 Async, SQLite/Alembic)
│   └── web/              # Frontend Web (Next.js 16 App Router, React 19, Tailwind CSS v4, Base UI)
├── docs/
│   ├── architecture/     # Detailed technical system architecture
│   ├── engineering/      # Engineering standards, Coding Standards, Naming Conventions
│   ├── frontend/         # Frontend architecture, implementation plans, and conventions
│   └── project-analysis/ # System audit reports and AI Guide migration records
├── AGENTS.md             # This document (Global Agent Entry Point)
└── README.md             # Root-level project introduction
```

---

## 2. Technology Reality Map

To prevent AI Agents from hallucinating uninstalled packages or unsupported architectural components, AI Agents must strictly distinguish between the **Active Runtime Reality** and **Future Planned Targets**:

| Component | Active Runtime Reality | Future Planned Targets (Not Installed) | Mandatory Rule for AI Agents |
| :--- | :--- | :--- | :--- |
| **Database** | **SQLite (`huce_kms.db`)** via `aiosqlite` | **PostgreSQL** (no `asyncpg` or `psycopg` drivers installed) | **DO NOT** attempt to connect to PostgreSQL or import PostgreSQL drivers. All queries MUST execute via SQLAlchemy 2.0 Async with SQLite. |
| **Vector DB / RAG** | Not installed; Frontend displays simulated SSE streaming | **Qdrant Vector Database**, Ragas | **DO NOT** `import qdrant_client` or invoke vector search until explicitly directed and dependencies are added to `pyproject.toml`. |
| **Backend Core** | FastAPI, Python 3.12, Pydantic V2, Pwdlib (Argon2id), PyJWT | Celery / Redis background workers | Strictly adhere to the layered architecture in `apps/backend/src/api/`. |
| **Frontend Core** | Next.js 16.4 (Turbopack), React 19.3, Tailwind CSS v4, Base UI, shadcn | Advanced Server Actions mutations | Strictly adhere to feature-driven modules in `src/features/` and Base UI primitives in `src/components/ui/`. |

---

## 3. Repository Boundaries

AI Agents must strictly honor the operational boundaries between sub-applications:

1. **Backend (`apps/backend`)**:
   - Manages dependencies independently using `uv` (via `pyproject.toml` and `uv.lock`).
   - Module root is configured at `src/`, with top-level imports rooted at `api.*`.
   - Responsible for providing standardized RESTful APIs, JWT authentication, RBAC, ORM persistence, and knowledge domain logic.
   - Dedicated instructions: See [apps/backend/AGENTS.md](file:///apps/backend/AGENTS.md).

2. **Frontend (`apps/web`)**:
   - Manages dependencies independently using `pnpm` (via `package.json` and `pnpm-lock.yaml`).
   - Built on Next.js 16 (App Router), React 19, Base UI, and Tailwind CSS v4.
   - Responsible for user interface, academic document lookup, real-time AI chat streaming (SSE), and system administration.
   - Dedicated instructions: See [apps/web/AGENTS.md](file:///apps/web/AGENTS.md).

3. **Technical Documentation (`docs/`)**:
   - Serves as the Single Source of Truth for all architectural designs, engineering rules, and implementation progress.
   - Any architectural changes or conventions MUST be kept in sync within this directory.

---

## 4. Global Engineering Principles

1. **Source of Truth Priority**:
   - In case of discrepancies between documentation and actual source code, the order of precedence is:
     1. Active running source code.
     2. Project configuration files (`pyproject.toml`, `package.json`, `alembic.ini`).
     3. Existing automated tests (if any).
     4. Technical documentation in `docs/`.
     5. User prompt requests.
   - Never assume a library or architectural pattern exists without verifying source files or configuration.

2. **Strict Non-Destructive Policy**:
   - Do not refactor modules outside the explicit scope of the current task.
   - Do not delete or rename API fields, database schema columns, or established directory structures without approval.
   - Never expose secrets, tokens, credentials, or private keys from `.env` files or configuration files.

3. **Separation of Concerns**:
   - Maintain strict separation across architectural layers: Route Handlers only process HTTP requests/responses, Services only handle business logic, and Repositories only execute data access.

---

## 5. AI Agent Implementation Workflow

### 5.1. Before Implementation
1. **Inspect Existing Code First**:
   - Always read reference implementations before writing new code. For example, before creating a new backend endpoint, inspect `api/v1/routes/users.py`, `api/services/user.py`, and `api/repositories/user.py`.
2. **Review Conventions**:
   - Consult [Coding Standards](file:///docs/engineering/coding-standards.md) and [Naming Conventions](file:///docs/engineering/naming-conventions.md).
3. **No Unapproved Dependencies**:
   - Only use libraries declared in `pyproject.toml` (Backend) or `package.json` (Frontend).
   - If a new dependency is strictly necessary, provide a clear technical justification and obtain user approval first.

### 5.2. After Implementation
1. **Syntax & Import Validation**:
   - Ensure all imports are valid with zero circular dependencies or unused imports.
   - Backend: Verify importability via `uv run python -c "import <module>"`.
   - Frontend: Verify with `pnpm exec tsc --noEmit` and `pnpm exec eslint .`.
2. **Formatting & Type Safety**:
   - Maintain strict type annotations (Python 3.12+ type hints, TypeScript strict typing).
3. **Documentation Updates**:
   - Update API specifications and implementation tracking documents whenever functional scope changes.

---

## 6. Technical Documentation References

| Subject | Document Location | Description |
| :--- | :--- | :--- |
| **Backend Agent Guidelines** | [apps/backend/AGENTS.md](file:///apps/backend/AGENTS.md) | Layered architecture, transaction management, and backend rules |
| **Frontend Agent Guidelines** | [apps/web/AGENTS.md](file:///apps/web/AGENTS.md) | Next.js 16, React 19, Tailwind v4, Base UI, and feature-driven patterns |
| **Project Audit Report** | [docs/project-analysis/project-audit.md](file:///docs/project-analysis/project-audit.md) | Full technical audit report and system findings |
| **AI Guide Update Plan** | [docs/project-analysis/ai-guide-update-plan.md](file:///docs/project-analysis/ai-guide-update-plan.md) | AI Guide modernization plan and governance strategy |
| **Backend Architecture** | [docs/architecture/backend-architecture.md](file:///docs/architecture/backend-architecture.md) | Layered architecture, request lifecycle, and database flow |
| **Coding Standards** | [docs/engineering/coding-standards.md](file:///docs/engineering/coding-standards.md) | Python standards, type hints, Pydantic, and SQLAlchemy |
| **Naming Conventions** | [docs/engineering/naming-conventions.md](file:///docs/engineering/naming-conventions.md) | Naming rules for files, classes, models, routes, and schemas |
| **Frontend Architecture** | [docs/frontend/architecture.md](file:///docs/frontend/architecture.md) | Next.js App Router, state management, and data fetching |
| **Frontend Conventions** | [docs/frontend/conventions.md](file:///docs/frontend/conventions.md) | React 19 standards, Tailwind CSS v4, and UI components |
| **Frontend Implementation Status** | [docs/frontend/implementation-status.md](file:///docs/frontend/implementation-status.md) | Progress tracker and delivery status |
