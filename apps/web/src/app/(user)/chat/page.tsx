"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { ChatComposer } from "@/features/chat"
import { ROUTES } from "@/constants/routes"

const suggestionPrompts = [
  {
    title: "Điều kiện xét tốt nghiệp",
    prompt: "Điều kiện để được xét công nhận tốt nghiệp đại học chính quy là gì?",
  },
  {
    title: "Quy định làm đồ án",
    prompt: "Thời gian và quy trình nộp đồ án tốt nghiệp khóa mới nhất được quy định thế nào?",
  },
  {
    title: "Tiêu chuẩn xét học bổng",
    prompt: "Tiêu chuẩn xét cấp học bổng khuyến khích học tập gồm những điều kiện gì?",
  },
]

export default function NewChatPage() {
  const router = useRouter()

  const handleSend = React.useCallback(
    (promptMessage: string) => {
      const trimmed = promptMessage.trim()
      if (!trimmed) return
      const newId = `thread-${Date.now()}`
      try {
        sessionStorage.setItem("huce_pending_query", trimmed)
      } catch {
        // Ignore storage error
      }
      router.push(ROUTES.USER.CHAT_DETAIL(newId))
    },
    [router]
  )

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center p-4 sm:p-6 lg:p-8">
      {/* Welcome Hero */}
      <div className="my-auto space-y-6 py-6 text-center">
        <div>
          <h1 className="font-heading text-2xl font-bold tracking-tight text-heading sm:text-3xl">
            Tôi có thể giúp gì cho bạn?
          </h1>
        </div>

        {/* Input Composer in Center */}
        <div className="w-full text-left">
          <ChatComposer onSend={handleSend} />
        </div>

        {/* Compact 1-line suggestion chips */}
        <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
          {suggestionPrompts.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(item.prompt)}
              className="inline-flex cursor-pointer items-center rounded-full border border-slate-200/80 bg-surface px-3.5 py-1.5 text-xs text-muted shadow-2xs transition-all hover:border-brand-primary/40 hover:bg-brand-primary/5 hover:text-brand-primary"
            >
              <span>{item.title}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
