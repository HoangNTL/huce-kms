"use client"

import * as React from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

interface ChatComposerProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
  className?: string
}

export function ChatComposer({
  onSend,
  disabled = false,
  placeholder = "Hỏi về quy chế đào tạo, học bổng, đồ án tốt nghiệp HUCE...",
  className,
}: ChatComposerProps) {
  const [input, setInput] = React.useState("")
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setInput("")
  }

  return (
    <div
      className={cn(
        "relative rounded-xl border border-border bg-surface p-2 shadow-xs transition-all focus-within:border-brand-primary focus-within:ring-1 focus-within:ring-brand-primary",
        className
      )}
    >
      <Textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={2}
        className="min-h-[50px] resize-none border-0 bg-transparent p-2 text-sm text-heading placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:outline-none"
      />
      <div className="flex items-center justify-between border-t border-border/50 px-2 pt-2">
        <p className="flex items-center gap-1 text-[11px] text-muted">
          <span>Nhấn</span>
          <kbd className="rounded border border-border bg-surface px-1 py-0.5 text-[10px] font-semibold text-muted">
            Enter ↵
          </kbd>
          <span>để gửi, Shift + Enter để xuống dòng</span>
        </p>

        <Button
          size="sm"
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="h-8 gap-1.5 bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
        >
          <span>Gửi</span>
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
