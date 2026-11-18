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
  placeholder = "Nhập câu hỏi của bạn...",
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
        "relative rounded-2xl border border-slate-200/90 bg-surface p-3 shadow-xs transition-all focus-within:border-brand-primary focus-within:ring-1 focus-within:ring-brand-primary",
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
        className="min-h-[50px] resize-none border-0 bg-transparent p-1 text-sm text-heading placeholder:text-slate-400 dark:placeholder:text-slate-500 focus-visible:ring-0 focus-visible:outline-none"
      />
      <div className="flex items-center justify-between pt-2">
        <span className="text-2xs text-muted hidden sm:inline">
          Shift + Enter để xuống dòng
        </span>

        <Button
          size="icon"
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="h-8 w-8 rounded-xl bg-brand-primary text-white shadow-xs hover:bg-brand-primary-hover disabled:opacity-30 ml-auto"
          aria-label="Gửi câu hỏi"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
