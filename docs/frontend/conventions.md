# HUCE KMS — Frontend Coding Conventions & Clean Architecture Standards

> **Project**: HUCE KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Frontend Coding Standards, Clean Code & Architectural Conventions  
> **Target**: Entire `apps/web` codebase (`Next.js 16.4`, `React 19.3`, `TypeScript 5.9`, `Tailwind CSS v4`, `Base UI`)  
> **Last Updated**: 2026-11-18  

Normative Classification:
- **MUST**: Absolute requirement. Violations must be rejected during code review.
- **SHOULD**: Strong recommendation. Can only be bypassed with explicit technical justification.
- **PROHIBITED**: Forbidden practice / anti-pattern.

---

## 1. Naming Conventions

### 1.1. Files & Directories (MUST)
- **kebab-case** for all directories and source files:
  - `src/components/layout/user-header.tsx`
  - `src/features/auth/components/login-form.tsx`
  - `src/lib/api-client.ts`
- **PROHIBITED**: Do NOT use `camelCase` or `PascalCase` for filenames.
- **Special Next.js Files**: Strictly adhere to Next.js App Router conventions:
  - `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`.

### 1.2. Variables, Functions & Identifiers (MUST)
- **camelCase**: Local variables, object properties, utility functions, hooks:
  - `const [isOpen, setIsOpen] = useState(false)`
  - `function formatDate(date: string): string`
  - `export function useDebounce<T>(value: T, delay: number): T`
- **PascalCase**: React components, TypeScript types, interfaces, enums:
  - `export function ChatComposer({ ... }: ChatComposerProps)`
  - `interface DocumentMetadata { ... }`
  - `type UserRole = "USER" | "ADMIN"`
- **UPPER_SNAKE_CASE**: Immutable constants and configuration dictionaries:
  - `export const ROUTES = { ... } as const`
  - `export const MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024`

---

## 2. Component Structure & File Granularity Standards

### 2.1. Single Responsibility Principle & File Length (MUST)
- **Thin Page Orchestrators**: Page components (`page.tsx`) **MUST** act solely as orchestrators/coordinators (handling layout composition, routing parameters, and assembling domain components). Monolithic page files (400+ lines) containing inline modals, tables, and complex forms are **PROHIBITED**.
- **File Length Thresholds**:
  - **Leaf / Atomic UI components**: `<= 150 lines`.
  - **Modals, Dialogs & Complex Forms**: `<= 200 lines`.
  - **Tables, Views & Complex Panels**: `<= 250 lines`.
  - **Page Orchestrators (`page.tsx`)**: `<= 200 lines`.
- **Sub-component Decomposition**: Any dialog or modal (e.g., `document-upload-modal.tsx`, `category-delete-dialog.tsx`) **MUST** be extracted into its own file under `src/features/<feature>/components/`.

### 2.2. Standard Component Blueprint
Every component file **MUST** adhere to the following organized layout:

```tsx
"use client" // Declare ONLY when component uses hooks, events, or browser APIs

import * as React from "react"

// 1. External dependencies & icons
import { useForm } from "react-hook-form"
import { LucideIcon, Send } from "lucide-react"

// 2. UI Primitives & Core Helpers
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// 3. Domain Features, Services & Types
import type { ChatMessage } from "../types"

// 4. Props Interface
interface ComponentNameProps {
  message: ChatMessage
  onAction?: () => void
  className?: string
}

// 5. Component Implementation
export function ComponentName({ message, onAction, className }: ComponentNameProps) {
  // 5.1. State & Hooks
  const [isLoading, setIsLoading] = React.useState(false)

  // 5.2. Derived Computations (Computed during render, NOT in useEffect)
  const isActionable = Boolean(message.content && !isLoading)

  // 5.3. Event Handlers
  const handleAction = async () => {
    if (!isActionable) return // Guard clause
    setIsLoading(true)
    try {
      await onAction?.()
    } finally {
      setIsLoading(false)
    }
  }

  // 5.4. Render Return
  return (
    <div className={cn("base-classes", className)}>
      <Button onClick={handleAction} disabled={!isActionable}>
        <Send className="h-4 w-4" />
        <span>Gửi tin nhắn</span>
      </Button>
    </div>
  )
}
```

---

## 3. React 19 & Next.js 16 App Router Standards

### 3.1. Server vs. Client Component Boundaries (MUST)
- All files in `app/` are **Server Components by default**.
- **Rule**: Only add the `"use client"` directive when a component:
  - Uses React hooks (`useState`, `useEffect`, `useCallback`, `useMemo`, `useRef`, `useTransition`).
  - Attaches DOM event listeners (`onClick`, `onChange`, `onSubmit`, `onKeyDown`).
  - Directly accesses browser APIs (`window`, `document`, `localStorage`).
- **Best Practice**: Keep Server Components as high-level layout containers; push `"use client"` down to interactive leaf nodes to maximize SSR and initial HTML streaming benefits.

### 3.2. Asynchronous Route Parameters in Next.js 16 (MUST)
- In Next.js 16, `params` and `searchParams` passed to Server Components are **Promises**:
  ```tsx
  interface PageProps {
    params: Promise<{ id: string }>
    searchParams: Promise<{ page?: string; tab?: string }>
  }

  export default async function DocumentDetailPage({ params, searchParams }: PageProps) {
    const { id } = await params
    const { page, tab } = await searchParams
    return <DocumentView documentId={id} page={Number(page) || 1} tab={tab ?? "overview"} />
  }
  ```

### 3.3. React 19 State Lifecycle: Prohibition of `setState` in `useEffect` (MUST)
- **STRICTLY PROHIBITED**: Calling `setState` synchronously or directly inside `useEffect` to synchronize props with state (`react-hooks/set-state-in-effect`).
- **Correct Practices**:
  - **Derive state during render**:
    ```tsx
    // Correct: Computed synchronously during render
    const fullName = `${user.firstName} ${user.lastName}`
    ```
  - **State resets belong in event handlers**:
    ```tsx
    // Correct: Reset pagination inside the search event handler
    const handleSearchChange = (query: string) => {
      setSearch(query)
      setCurrentPage(1) // Reset state directly in handler
    }
    ```

### 3.4. Route Metadata & SEO (MUST)
- Every route **MUST** export either a static `metadata: Metadata` object or an async `generateMetadata()` function:
  ```tsx
  import type { Metadata } from "next"

  export const metadata: Metadata = {
    title: "Tra cứu Tài liệu & Quy chế | HUCE KMS",
    description: "Hệ thống quản lý tài liệu và quy định học tập Trường Đại học Xây dựng Hà Nội.",
  }
  ```

---

## 4. Styling Rules with Tailwind CSS v4

### 4.1. Semantic CSS Tokens (MUST)
- **PROHIBITED**: Never hardcode arbitrary hex colors (`#0f5ba6`, `#1e293b`).
- **Rule**: Always use the semantic CSS variables configured in `src/app/globals.css`:
  - **Brand**: `bg-brand-primary`, `hover:bg-brand-primary-hover`, `text-brand-primary`, `bg-brand-primary-subtle`.
  - **Surfaces**: `bg-background`, `bg-surface`, `bg-muted`.
  - **Typography**: `text-heading`, `text-body`, `text-muted`.
  - **Feedback**: `text-success`, `bg-warning/10`, `text-destructive`.
  - **Borders**: `border-border`, `border-sidebar-border`.

### 4.2. Class Name Merging via `cn()` (MUST)
- Always use `cn()` from `@/lib/utils` to merge class names safely without specificity conflicts:
  ```tsx
  import { cn } from "@/lib/utils"

  export function CustomBadge({ className, ...props }: BadgeProps) {
    return <span className={cn("inline-flex items-center px-2 py-0.5 rounded-md", className)} {...props} />
  }
  ```
- ⚠️ **shadcn CLI Import Caveat**: `pnpm dlx shadcn@latest add ...` may erroneously generate imports `from "cn"` instead of `from "@/lib/utils"`. When adding components, verify and correct this import path.

### 4.3. Class Sorting
- Code formatting automatically organizes Tailwind utility classes via `prettier-plugin-tailwindcss` during `pnpm run format`.

### 4.4. CSS Unit Conventions (MUST)
- **`rem` for Typography**: All font sizes **MUST** use `rem` via Tailwind utility classes (`text-3xs`, `text-2xs`, `text-xs`, `text-sm`, `text-base`, `text-lg`, `text-xl`,...). **STRICTLY PROHIBITED**: Hardcoding arbitrary pixel values like `text-[11px]` or `text-[12px]` to preserve browser accessibility (a11y) and user font scaling.
- **`%` for Fluid Layouts**: Use `w-full` (100%) and `h-full` (100%) combined with Flexbox (`flex-1`), CSS Grid (`fr`), and max-width containers (`rem`) to ensure responsive layout fluidity.
- **`w-full` & `min-h-screen` for Full-screen Sections**: Always use `w-full` instead of `100vw` (to avoid horizontal scrollbar overflow bugs on desktop browsers) and use `min-h-screen` / `min-h-dvh` for viewport height.
- **`px` for Borders & Radii**: Keep border widths (`border`, `border-t`, `border-2`) and corner radii (`--radius: 8px`) in `px` for pixel-perfect sharpness across all display densities.

---

## 5. TypeScript & Strict Type Safety Standards

### 5.1. Zero-`any` Policy (MUST)
- **STRICTLY PROHIBITED**: Using `any` or casting with `as any`.
- **Alternative**: Use `unknown` with type narrowing (type guards, `typeof`, `instanceof`), or parse with Zod schemas.

### 5.2. Explicit Type-Only Imports (MUST)
- **Rule**: Types and interfaces **MUST** be imported using `import type`:
  ```tsx
  // Correct
  import type { UserResponse, UserRole } from "@/types/user"
  import type { Metadata } from "next"

  // Incorrect (Avoid bundling types as runtime JS)
  import { UserResponse } from "@/types/user"
  ```

### 5.3. `interface` vs. `type` Conventions (MUST)
- **`interface`**: **MUST** be used for React component props and extendable domain objects:
  ```tsx
  export interface UserCardProps {
    user: UserResponse
    onEdit?: (user: UserResponse) => void
  }
  ```
- **`type`**: **MUST** be used for unions, intersections, primitives, tuples, and utility types:
  ```tsx
  export type TabKey = "overview" | "chunks" | "metadata"
  export type Nullable<T> = T | null
  ```

### 5.4. Explicit Return Types (SHOULD)
- All public API services, custom hooks, and utility functions **SHOULD** declare explicit return types:
  ```tsx
  export async function fetchDocuments(params: DocumentQueryParams): Promise<DocumentListResponse> {
    return apiClient.get<DocumentListResponse>("/documents", { params })
  }
  ```

---

## 6. Data Fetching, API & UI State Machine Standards

### 6.1. Centralized Service Layer (MUST)
- **PROHIBITED**: Calling native `fetch()` or `axios` directly inside components.
- **Rule**: All HTTP requests **MUST** be defined in `src/features/<feature>/services/<feature>-service.ts` using `apiClient` (`src/lib/api-client.ts`).
- `apiClient` automatically injects Bearer JWT authentication, auto-refreshes tokens on `401 Unauthorized`, and unwraps the `BaseResponse[T]` envelope.

### 6.2. Mandatory Triple UI State Handling (MUST)
Every asynchronous data view **MUST** implement three distinct visual states:
1. **Loading State**: Render a dedicated `<Skeleton />`, `<TableSkeleton />`, or loading indicator while data is being fetched. Never render a blank screen.
2. **Empty State**: When the fetched list is empty (`items.length === 0`), render an informative empty feedback widget (`<EmptyState />` or `<EmptyMedia />`) with an actionable CTA button.
3. **Error State**: Caught errors **MUST** provide actionable user feedback via `sonner` (`toast.error(...)`) or an inline error alert banner.

### 6.3. User Feedback & Notifications
- Use `sonner` for toast notifications:
  - Success: `toast.success("Cập nhật danh mục thành công")`
  - Error: `toast.error(error.message || "Không thể tải danh sách tài liệu. Vui lòng thử lại.")`
- **Rule**: All user-facing error messages **MUST** be in clean, grammatically correct Vietnamese. Never display raw stack traces, SQL errors, or unformatted HTTP status codes to users.

---

## 7. Form Handling & Validation Standards

1. Every user input form **MUST** define its validation schema using **Zod** (`zod@^4` or compat).
2. Connect Zod schemas to **React Hook Form** via `@hookform/resolvers/zod`.
3. Validation error messages **MUST** render immediately below the respective input field (`text-xs text-destructive`).
4. Always handle `disabled` states and loading indicators during submission (`disabled={isSubmitting}`).
5. Reset forms on successful submission or modal close (`form.reset()`).

---

## 8. Accessibility (A11y) & Semantic HTML Standards

### 8.1. Accessible Interactive Elements (MUST)
- All icon-only buttons (`<Button size="icon">` or buttons lacking text content) **MUST** include an accessible name via `aria-label` or `title`:
  ```tsx
  // Correct
  <Button size="icon" variant="ghost" aria-label="Xóa tài liệu" title="Xóa tài liệu" onClick={handleDelete}>
    <Trash2 className="h-4 w-4 text-destructive" />
  </Button>

  // Incorrect (Inaccessible to screen readers)
  <Button size="icon" variant="ghost" onClick={handleDelete}>
    <Trash2 className="h-4 w-4" />
  </Button>
  ```

### 8.2. Semantic HTML Layout (MUST)
- Use semantic HTML tags instead of nested `<div>` wrappers:
  - `<header>` for page and section banners.
  - `<main>` for primary page content.
  - `<nav>` for navigation bars and menus.
  - `<aside>` for sidebars and auxiliary panels.
  - `<footer>` for page and card footers.

### 8.3. Images & Media (MUST)
- Next.js `<Image />` components **MUST** provide a descriptive, meaningful `alt` attribute. If an image is purely decorative, specify `alt=""`.

---

## 9. Clean Code & Code Smell Checklist

- **No Magic Strings or Numbers**:
  - Route navigation paths **MUST** reference `ROUTES` from `@/constants/routes`.
  - Roles, document statuses, and constants **MUST** reference typed dictionaries (`ROLE_LABELS`, `DOCUMENT_STATUS`).
- **Guard Clauses & Early Returns**:
  - Favor early returns over deeply nested `if / else` blocks to keep cyclomatic complexity low:
    ```tsx
    // Correct
    if (!user) return <LoadingSpinner />
    if (!user.isActive) return <AccountLockedAlert />
    return <UserProfileView user={user} />
    ```
- **Zero Debugging Artifacts**:
  - **PROHIBITED**: `console.log`, `debugger`, or commented-out dead code blocks in commits.
- **URL as Single Source of Truth for Filters**:
  - Filter state, search queries, pagination numbers, and active tabs in data tables **SHOULD** synchronize with URL `searchParams` whenever shareable or bookmarkable links provide better UX.

---

## 10. Code Quality & CI/CD Verification Scripts

Before committing or opening a pull request, developers and AI agents **MUST** execute and pass all verification scripts with Exit Code 0:

```bash
# 1. Verify code formatting
pnpm run format:check

# 2. Run ESLint checks
pnpm run lint

# 3. Verify TypeScript type safety
pnpm run typecheck

# 4. Verify Next.js production build
pnpm run build
```
All commands **MUST** succeed with Exit Code 0 without unresolved lint or typecheck errors.
