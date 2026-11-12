"use client"

import * as React from "react"
import { Sparkles, BookOpen, Loader2 } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  ChatComposer,
  CitationBadge,
  FeedbackButtons,
  useRAGStream,
} from "@/features/chat"
import { cn } from "@/lib/utils"

interface ChatDetailPageProps {
  params: Promise<{ id: string }>
}

export default function ChatDetailPage({ params }: ChatDetailPageProps) {
  const resolvedParams = React.use(params)
  const threadId = resolvedParams.id
  const { messages, isLoading, sendMessage } = useRAGStream(threadId)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  // Check and consume initial pending query if redirected from new chat page
  const hasTriggeredInitial = React.useRef(false)
  React.useEffect(() => {
    if (hasTriggeredInitial.current) return
    try {
      const pending = sessionStorage.getItem("huce_pending_query")
      if (pending) {
        sessionStorage.removeItem("huce_pending_query")
        hasTriggeredInitial.current = true
        sendMessage(pending)
      }
    } catch {
      // Ignore storage error
    }
  }, [sendMessage])

  // Scroll to bottom on new messages or streamed tokens
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isLoading])

  const handleSend = (content: string) => {
    sendMessage(content)
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-between p-4 sm:p-6 lg:p-8">
      {/* Thread title header */}
      <div className="mb-4 flex items-center justify-between border-b border-border/50 pb-3 text-xs text-muted">
        <span>Phiên hỏi đáp #{threadId}</span>
        <span className="flex items-center gap-1.5 text-[11px]">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          RAG Pipeline (FastAPI + Qdrant + Gemini)
        </span>
      </div>

      {/* Message history */}
      <div className="flex-1 space-y-6 overflow-y-auto pb-6">
        {messages.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center gap-2 text-center text-xs text-muted">
            <Sparkles className="h-8 w-8 text-brand-primary/50" />
            <p className="font-medium text-heading">Bắt đầu phiên hỏi đáp mới</p>
            <p>Nhập câu hỏi bên dưới để tra cứu quy chế, thông báo và văn bản HUCE.</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex items-start gap-3 text-sm",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {/* Assistant AI Avatar */}
              {msg.role === "assistant" && (
                <Avatar className="mt-0.5 h-8 w-8 shrink-0 border border-border shadow-xs">
                  <AvatarFallback className="bg-brand-primary text-white">
                    <Sparkles className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}

              {/* Bubble */}
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl p-4 shadow-xs",
                  msg.role === "user"
                    ? "rounded-tr-xs bg-brand-primary text-white"
                    : "space-y-3 rounded-tl-xs border border-border bg-surface text-heading"
                )}
              >
                {/* Content or Loader */}
                {msg.role === "assistant" && !msg.content ? (
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                    <span>Đang đối chứng tài liệu và suy luận câu trả lời...</span>
                  </div>
                ) : (
                  <div className="text-xs leading-relaxed whitespace-pre-wrap sm:text-sm">
                    {msg.content}
                  </div>
                )}

                {/* Citations badges for assistant */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="border-t border-border/50 pt-2">
                    <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-brand-primary">
                      <BookOpen className="h-3 w-3" />
                      <span>Tài liệu đối chứng đã tham chiếu:</span>
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.citations.map((cite, idx) => (
                        <CitationBadge
                          key={cite.chunk_index !== undefined ? cite.chunk_index : idx}
                          citation={cite}
                          index={idx}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Assistant actions: Copy, Feedback */}
                {msg.role === "assistant" && msg.content && (
                  <div className="flex items-center justify-between border-t border-border/30 pt-1">
                    <span className="text-[10px] text-muted">{msg.created_at}</span>
                    <FeedbackButtons messageId={msg.id} contentToCopy={msg.content} />
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <div className="sticky bottom-4 w-full pt-4">
        <ChatComposer onSend={handleSend} disabled={isLoading} />
      </div>
    </div>
  )
}
