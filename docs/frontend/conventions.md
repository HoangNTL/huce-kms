# HUCE KMS — Frontend Coding Conventions

> **Project**: HUCE KMS (Knowledge Management System & AI Assistant - Hanoi University of Civil Engineering)  
> **Document**: Frontend Coding Standards & Best Practices  
> **Target**: Entire `apps/web` codebase  
> **Last Updated**: 2026-11-08

---

## 1. Naming Conventions

### 1.1. Files & Directories
- **kebab-case** for all directories and source files:
  - `src/components/layout/user-header.tsx`
  - `src/features/auth/components/login-form.tsx`
  - `src/lib/api-client.ts`
- **DO NOT** use camelCase or PascalCase for filenames.
- **Special Next.js Files**: Strictly adhere to Next.js App Router conventions:
  - `page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`, `not-found.tsx`.

### 1.2. Variables, Functions & Identifiers
- **camelCase**: Local variables, object properties, utility functions:
  - `const [isOpen, setIsOpen] = useState(false)`
  - `function formatDate(date: string): string`
- **PascalCase**: React components, TypeScript types, interfaces, enums:
  - `export function ChatComposer({ ... })`
  - `interface DocumentMetadata { ... }`
  - `type UserRole = "USER" | "ADMIN"`
- **UPPER_SNAKE_CASE**: Immutable constants and route dictionaries:
  - `export const ROUTES = { ... } as const`

---

## 2. Component Structure Standard

```tsx
"use client" // Declare ONLY when the component uses hooks, state, or browser APIs

import * as React from "react"

// 1. External dependencies
import { useForm } from "react-hook-form"
import { LucideIcon, Send } from "lucide-react"

// 2. UI Primitives & Core Helpers
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// 3. Domain Types
import type { ChatMessage } from "../types"

// 4. Props Interface
interface ComponentProps {
  message: ChatMessage
  onAction?: () => void
  className?: string
}

// 5. Component Implementation
export function ComponentName({ message, onAction, className }: ComponentProps) {
  // Hooks
  const [loading, setLoading] = React.useState(false)

  // Event Handlers
  const handleClick = () => {
    // ...
  }

  // Render
  return (
    <div className={cn("base-classes", className)}>
      {/* JSX */}
    </div>
  )
}
```

---

## 3. Styling Rules with Tailwind CSS v4

1. **No Hardcoded Hex Colors**:
   - Always use the semantic CSS variables configured in `globals.css`:
   - Brand: `bg-brand-primary`, `hover:bg-brand-primary-hover`, `text-brand-primary`, `bg-brand-primary-subtle`.
   - Layout: `bg-background`, `bg-surface`, `text-heading`, `text-body`, `text-muted`, `border-border`.
2. **Use the `cn()` Utility**:
   - Merge class names safely without Tailwind specificity conflicts:
   ```tsx
   className={cn(
     "px-4 py-2 rounded-lg bg-surface",
     isActive && "bg-brand-primary-subtle text-brand-primary",
     className
   )}
   ```
3. **Class Sorting**:
   - Maintain automatic class sorting via `prettier-plugin-tailwindcss` during formatting (`pnpm run format`).

---

## 4. Form Handling & Validation Standards

1. Every user input form **MUST** define its validation schema using **Zod**.
2. Connect Zod schemas to **React Hook Form** via `@hookform/resolvers/zod`.
3. Validation error messages **MUST** render immediately below the input field (`text-xs text-destructive`).
4. Always handle `disabled` states and loading indicators during submission (`isLoading`).

---

## 5. Code Quality & CI/CD Verification Scripts

Before committing or opening a pull request, developers **MUST** verify that all 4 commands pass with Exit Code 0 and zero warnings:

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
