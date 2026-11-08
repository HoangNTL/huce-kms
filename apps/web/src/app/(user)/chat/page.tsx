"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Sparkles, BookOpen, GraduationCap, FileCheck2, ArrowRight } from "lucide-react"
import { ChatComposer } from "@/features/chat"
import { ROUTES } from "@/constants/routes"

const suggestionPrompts = [
  {
    icon: GraduationCap,
    title: "Quy chế Đào tạo",
    prompt: "Điều kiện để được xét công nhận tốt nghiệp đại học chính quy là gì?",
  },
  {
    icon: BookOpen,
    title: "Đồ án Tốt nghiệp",
    prompt: "Thời gian và quy trình nộp đồ án tốt nghiệp khóa mới nhất được quy định thế nào?",
  },
  {
    icon: FileCheck2,
    title: "Học bổng & Học phí",
    prompt: "Tiêu chuẩn xét cấp học bổng khuyến khích học tập kỳ vừa qua gồm những điều kiện gì?",
  },
]

export default function NewChatPage() {
  const router = useRouter()

  const handleSend = React.useCallback(
    (promptMessage: string) => {
      // Store initial query if needed and navigate to new thread
      const randomSuffix = Math.random().toString(36).substring(2, 8)
      const newId = `thread-${randomSuffix}`
      if (promptMessage) {
        // Ready for session init
      }
      router.push(ROUTES.USER.CHAT_DETAIL(newId))
    },
    [router]
  )

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-between p-4 sm:p-6 lg:p-8">
      {/* Welcome Hero */}
      <div className="my-auto space-y-4 py-10 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-brand-primary/20 bg-brand-primary-subtle text-brand-primary shadow-xs">
          <Sparkles className="h-7 w-7" />
        </div>

        <div className="space-y-2">
          <h1 className="font-heading text-2xl font-bold text-heading sm:text-3xl">
            Xin chào! Tôi có thể giúp gì cho bạn hôm nay?
          </h1>
          <p className="mx-auto max-w-lg text-sm text-muted">
            Hỏi bất kỳ điều gì về quy chế đào tạo, thủ tục sinh viên, học bổng hoặc văn bản chính
            thức của Trường Đại học Xây dựng Hà Nội.
          </p>
        </div>

        {/* Suggestion cards */}
        <div className="mx-auto grid max-w-3xl grid-cols-1 gap-3 pt-6 text-left sm:grid-cols-3">
          {suggestionPrompts.map((item, idx) => {
            const Icon = item.icon
            return (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(item.prompt)}
                className="group flex cursor-pointer flex-col justify-between rounded-xl border border-border bg-surface p-4 text-left shadow-xs transition-all hover:border-brand-primary/50 hover:bg-brand-primary/5"
              >
                <div>
                  <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-brand-primary">
                    <Icon className="h-4 w-4" />
                    <span>{item.title}</span>
                  </div>
                  <p className="line-clamp-2 text-xs leading-relaxed text-body">"{item.prompt}"</p>
                </div>
                <div className="mt-3 flex items-center text-[11px] font-medium text-brand-primary opacity-0 transition-opacity group-hover:opacity-100">
                  <span>Hỏi ngay</span>
                  <ArrowRight className="ml-1 h-3 w-3" />
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Input Composer at Bottom */}
      <div className="sticky bottom-4 w-full pt-4">
        <ChatComposer onSend={handleSend} />
      </div>
    </div>
  )
}
