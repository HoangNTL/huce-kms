import * as React from "react"
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

export interface LoadingSpinnerProps {
  size?: "xs" | "sm" | "md" | "lg" | "xl"
  label?: string
  className?: string
  orientation?: "horizontal" | "vertical"
  fullScreen?: boolean
}

export function LoadingSpinner({
  size = "md",
  label,
  className,
  orientation = "horizontal",
  fullScreen = false,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    xs: "h-3.5 w-3.5",
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
    xl: "h-10 w-10",
  }

  const content = (
    <div
      className={cn(
        "flex items-center justify-center text-muted",
        orientation === "vertical" ? "flex-col gap-3" : "gap-2",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Loader2 className={cn("animate-spin text-brand-primary", sizeClasses[size])} />
      {label && <span className="text-xs font-medium text-slate-600 dark:text-slate-400">{label}</span>}
      <span className="sr-only">Đang tải...</span>
    </div>
  )

  if (fullScreen) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-background">
        {content}
      </div>
    )
  }

  return content
}
