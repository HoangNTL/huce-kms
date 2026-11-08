"use client"

import * as React from "react"
import { Check, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface PasswordChecklistProps {
  password: string
  className?: string
}

export function PasswordChecklist({ password, className }: PasswordChecklistProps) {
  const rules = [
    { label: "Ít nhất 8 ký tự", passed: password.length >= 8 },
    { label: "Chứa ít nhất 1 chữ hoa (A-Z)", passed: /[A-Z]/.test(password) },
    { label: "Chứa ít nhất 1 chữ số (0-9)", passed: /[0-9]/.test(password) },
    { label: "Chứa ít nhất 1 ký tự đặc biệt (!@#$...)", passed: /[^A-Za-z0-9]/.test(password) },
  ]

  return (
    <div
      className={cn(
        "space-y-1.5 rounded-lg border border-border bg-surface/50 p-3 text-xs",
        className
      )}
    >
      <p className="font-medium text-heading">Yêu cầu bảo mật mật khẩu:</p>
      <div className="grid grid-cols-1 gap-1.5 pt-1 sm:grid-cols-2">
        {rules.map((rule, idx) => (
          <div key={idx} className="flex items-center gap-1.5">
            {rule.passed ? (
              <Check className="h-3.5 w-3.5 shrink-0 text-success" />
            ) : (
              <X className="h-3.5 w-3.5 shrink-0 text-muted" />
            )}
            <span className={cn(rule.passed ? "font-medium text-success" : "text-muted")}>
              {rule.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
