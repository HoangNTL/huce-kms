# HUCE KMS — Frontend Folder Structure & Routing Map

> **Project**: HUCE KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Folder Structure & Route Specification  
> **Framework**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4, Base UI / shadcn (base-nova)  
> **Last Updated**: 2026-11-08

---

## 1. Project Organization Overview

The frontend operates as an independent application inside `apps/web` with its own isolated dependencies, configuration, and scripts:

```text
huce-kms/
├── apps/
│   ├── backend/                      # FastAPI Backend (Python 3.12, SQLAlchemy, uv - isolated)
│   └── web/                          # Next.js 16 Frontend (Isolated, all packages & config located here)
│       ├── package.json              # Web dependencies & scripts
│       ├── pnpm-lock.yaml            # Web dedicated lockfile
│       ├── .gitignore                # Web dedicated gitignore
│       ├── tsconfig.json             # TypeScript configuration
│       ├── next.config.ts            # Next.js configuration
│       └── src/                      # Frontend source code
└── docs/
    └── frontend/                     # Technical design, architecture & progress documentation
        ├── architecture.md           # System architecture & design tokens
        ├── conventions.md            # Coding standards & validation rules
        ├── folder-structure.md       # Directory structure & routing hierarchy
        ├── implementation-plan.md    # Multi-phase development roadmap
        └── implementation-status.md  # Delivery status & progress tracking
```

---

## 2. App Router Architecture (`apps/web/src/app`)

Next.js App Router utilizes Route Groups `(...)` to define clear layout boundaries, user contexts, and access control across subsystems:

```text
apps/web/src/app/
├── (auth)/                           # Authentication Subsystem
│   ├── layout.tsx                    # Centered layout, Academic Blue theme, HUCE Logo
│   ├── login/
│   │   └── page.tsx                  # Login Page (username/email, password, toggle visibility)
│   └── register/
│       └── page.tsx                  # Registration Page (real-time password requirement checklist)
│
├── (user)/                           # Standard User Subsystem (Role: USER)
│   ├── layout.tsx                    # User Layout: Chat History Sidebar + Top Header + User Menu
│   ├── chat/
│   │   ├── page.tsx                  # New Conversation Initialization View
│   │   └── [id]/
│   │       └── page.tsx              # Interactive RAG QA View:
│   │                                 # - SSE streaming conversation
│   │                                 # - Citations: inspect underlying reference documents
│   │                                 # - Like/dislike feedback
│   └── profile/
│       └── page.tsx                  # Personal profile overview & password update
│
├── (admin)/admin/                    # Administrative Subsystem (Role: ADMIN)
│   ├── layout.tsx                    # Admin Layout: Admin Navigation Sidebar + Top Bar
│   ├── page.tsx                      # Automatic redirect to /admin/dashboard
│   ├── dashboard/
│   │   └── page.tsx                  # Administrative Dashboard: knowledge metrics, charts, service health
│   ├── users/
│   │   └── page.tsx                  # User Management: data table, search, filtering, lock/unlock, role edit
│   ├── documents/
│   │   ├── page.tsx                  # Regulatory Document Management: list, RAG status, upload modal
│   │   └── [id]/
│   │       └── page.tsx              # Document Details: inspect extracted chunks & edit metadata
│   ├── crawler/
│   │   └── page.tsx                  # Crawler Management: source URLs & crawling job monitoring
│   └── profile/
│       └── page.tsx                  # Super Admin profile overview & logout
│
├── api/                              # Route Handlers (proxies or webhooks if required)
├── globals.css                       # Tailwind CSS v4 + Design Tokens CSS Variables
├── layout.tsx                        # Root Layout (Be Vietnam Pro font, Theme Provider, Toaster)
└── page.tsx                          # Root Page (Auth Guard -> redirect to /chat or /login)
```

---

## 3. Feature-driven Code Structure (`apps/web/src/features`)

The codebase adheres to **Feature-driven Co-location** to ensure self-contained, testable, and modular feature logic:

```text
apps/web/src/features/
├── auth/                             # Authentication Feature
│   ├── components/
│   │   ├── login-form.tsx            # Login form component
│   │   ├── register-form.tsx         # Registration form component
│   │   └── password-checklist.tsx    # Password requirement checklist
│   ├── schemas/
│   │   └── auth-schemas.ts           # Zod validation schemas
│   ├── services/
│   │   └── auth-service.ts           # API integration: /auth/login, /auth/register, /auth/logout
│   └── hooks/
│       └── use-auth.ts               # Authentication state management hook
│
├── chat/                             # AI Assistant & QA Feature
│   ├── components/
│   │   ├── chat-message-list.tsx     # Message conversation list
│   │   ├── chat-composer.tsx         # Prompt input textarea supporting Enter / Shift+Enter
│   │   ├── chat-bubble.tsx           # User query and AI response chat bubbles
│   │   ├── chat-history-sidebar.tsx  # Conversation history sidebar grouped by date
│   │   ├── citation-badge.tsx        # Inline citation badges linking claims to source documents
│   │   ├── citation-preview.tsx      # Modal / Popover displaying verbatim reference excerpts
│   │   └── feedback-buttons.tsx      # AI response like/dislike feedback actions
│   ├── stores/
│   │   └── use-chat-store.ts         # Active conversation state and streaming buffer
│   └── services/
│       └── chat-service.ts           # API integration: /chat/completions (SSE), /chat/conversations
│
├── documents/                        # Regulatory Document Management Feature
│   ├── components/
│   │   ├── document-table.tsx        # Regulatory document table
│   │   ├── document-columns.tsx      # TanStack Table column definitions
│   │   ├── document-upload-modal.tsx # Drag-and-drop PDF/DOCX upload modal
│   │   ├── document-metadata-form.tsx# Document metadata inspection and edit form
│   │   └── document-status-badge.tsx # RAG status badge (EXTRACTED, INDEXED, etc.)
│   └── services/
│       └── document-service.ts       # API integration: /documents/upload, /documents/{id}...
│
├── crawler/                          # Web Crawler Source & Job Feature
│   ├── components/
│   │   ├── crawl-source-table.tsx    # Crawl target source URL table
│   │   ├── crawl-source-modal.tsx    # Create/edit crawl source modal
│   │   ├── crawl-job-list.tsx        # Crawl job execution progress table
│   │   └── crawl-job-controls.tsx    # Job controls: start, pause, resume crawl tasks
│   └── services/
│       └── crawler-service.ts        # API integration: /crawler/sources, /crawler/jobs...
│
├── users/                            # User Administration Feature
│   ├── components/
│   │   ├── user-table.tsx            # User list data table
│   │   ├── user-status-switch.tsx    # Account active/inactive toggle switch
│   │   └── user-role-dialog.tsx      # Role assignment dialog (USER / ADMIN)
│   └── services/
│       └── user-service.ts           # API integration: /users, /users/{id}/status, /users/{id}/role
│
└── dashboard/                        # Overview & Analytics Feature
    ├── components/
    │   ├── metric-card.tsx           # Metric cards (documents, chunks, user counts)
    │   ├── document-status-chart.tsx # Document processing status distribution chart
    │   └── system-health-card.tsx    # Backend API and database health status card
    └── services/
        └── dashboard-service.ts      # Dashboard aggregation service
```

---

## 4. Shared Architecture Layer (`apps/web/src/`)

```text
apps/web/src/
├── components/
│   ├── ui/                           # Atomic primitives (Base UI + shadcn base-nova)
│   │   ├── button.tsx, input.tsx, card.tsx, dialog.tsx, sheet.tsx, table.tsx...
│   ├── layout/                       # Shared layout components
│   │   ├── header.tsx                # Main top navigation header
│   │   ├── user-menu.tsx             # User profile dropdown & logout trigger
│   │   └── sidebar-nav.tsx           # Sidebar navigation menu item renderer
│   └── shared/                       # Shared utility components
│       ├── empty-state.tsx           # Empty dataset placeholder
│       ├── loading-spinner.tsx       # Loading indicator spinner
│       └── confirm-dialog.tsx        # Confirmation dialog for critical actions (delete, lock)
│
├── hooks/                            # Custom React Hooks
│   ├── use-debounce.ts               # Search input debouncing
│   └── use-media-query.ts            # Responsive breakpoint detection for mobile/tablet
│
├── lib/                              # Core Utilities & Infrastructure
│   ├── utils.ts                      # cn() helper merging clsx and tailwind-merge
│   ├── sse.ts                        # Server-Sent Events parser wrapper for AI chatbot
│   └── api-client.ts                 # HTTP fetch client with automated silent token refresh
│
├── stores/                           # Global Zustand Stores
│   ├── use-sidebar-store.ts          # Sidebar collapse/expand state
│   └── use-theme-store.ts            # Theme preference store
│
├── types/                            # Shared TypeScript Types
│   ├── api.ts                        # ApiResponse, Pagination, ApiError contracts
│   └── user.ts                       # UserRole enum, UserProfile interface
│
├── constants/                        # Global Constants
│   └── routes.ts                     # Centralized application route definitions
└── config/
    └── site.ts                       # HUCE KMS product metadata & branding configuration
```
