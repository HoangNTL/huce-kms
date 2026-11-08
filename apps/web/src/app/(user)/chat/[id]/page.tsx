"use client"

import * as React from "react"
import { Sparkles, BookOpen } from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ChatComposer, CitationBadge, FeedbackButtons, type ChatMessage } from "@/features/chat"
import { cn } from "@/lib/utils"

interface ChatDetailPageProps {
  params: Promise<{ id: string }>
}

const sampleMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Cho tôi biết điều kiện để được nhận học bổng khuyến khích học tập tại HUCE?",
    createdAt: "10:30 AM",
  },
  {
    id: "msg-2",
    role: "assistant",
    content:
      "Theo Quy chế Công tác Sinh viên và Quy định Xét cấp Học bổng của Trường Đại học Xây dựng Hà Nội, để được xét cấp học bổng khuyến khích học tập, sinh viên cần đáp ứng các điều kiện cốt lõi sau:\n\n1. Kết quả học tập: Điểm trung bình chung học kỳ đạt từ loại Khá trở lên (từ 2.5/4.0 hoặc 7.0/10 trở lên) và không có học phần nào bị điểm F.\n2. Kết quả rèn luyện: Điểm rèn luyện trong kỳ đạt từ loại Khá trở lên (từ 70 điểm trở lên).\n3. Tín chỉ tích lũy: Phải đăng ký và tích lũy tối thiểu số tín chỉ theo quy định của khung chương trình trong học kỳ xét học bổng.",
    citations: [
      {
        documentId: "doc-hb-2023",
        documentTitle: "Quy định số 142/QĐ-ĐHXD về Xét cấp Học bổng Khuyến khích Học tập",
        chunkId: "chunk-hb-04",
        snippet:
          "Điều 5. Tiêu chuẩn xét, cấp học bổng: Sinh viên có kết quả học tập và rèn luyện từ loại khá trở lên, không bị kỷ luật từ mức khiển trách trở lên trong học kỳ xét học bổng. Điểm TBC học kỳ >= 2.50 và Điểm rèn luyện >= 70.",
        pageNumber: 3,
        score: 0.94,
      },
      {
        documentId: "doc-ctsv-2022",
        documentTitle: "Sổ tay Sinh viên HUCE - Phần Quy chế Đào tạo & Khen thưởng",
        chunkId: "chunk-ctsv-18",
        snippet:
          "Học bổng được xét theo thứ tự từ mức Xuất sắc, Giỏi đến Khá cho đến khi hết quỹ học bổng của ngành/khoa phân bổ.",
        pageNumber: 42,
        score: 0.88,
      },
    ],
    createdAt: "10:31 AM",
  },
]

export default function ChatDetailPage({ params }: ChatDetailPageProps) {
  const resolvedParams = React.use(params)
  const [messages, setMessages] = React.useState<ChatMessage[]>(sampleMessages)

  const handleSend = (content: string) => {
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      content,
      createdAt: "Bây giờ",
    }
    setMessages((prev) => [...prev, userMsg])

    // Simulate assistant reply
    setTimeout(() => {
      const assistantMsg: ChatMessage = {
        id: `msg-reply-${Date.now()}`,
        role: "assistant",
        content: `Đang tra cứu cơ sở dữ liệu tri thức HUCE cho câu hỏi: "${content}"...`,
        createdAt: "Bây giờ",
      }
      setMessages((prev) => [...prev, assistantMsg])
    }, 600)
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-between p-4 sm:p-6 lg:p-8">
      {/* Thread title header */}
      <div className="mb-4 flex items-center justify-between border-b border-border/50 pb-3 text-xs text-muted">
        <span>Phiên hỏi đáp #{resolvedParams.id}</span>
        <span className="text-[11px]">Mô hình: RAG Hybrid (FastAPI + Qdrant)</span>
      </div>

      {/* Message history */}
      <div className="flex-1 space-y-6 overflow-y-auto pb-6">
        {messages.map((msg) => (
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
              <div className="text-xs leading-relaxed whitespace-pre-wrap sm:text-sm">
                {msg.content}
              </div>

              {/* Citations badges for assistant */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="border-t border-border/50 pt-2">
                  <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-brand-primary">
                    <BookOpen className="h-3 w-3" />
                    <span>Tài liệu đối chứng đã tham chiếu:</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.citations.map((cite, idx) => (
                      <CitationBadge key={cite.chunkId} citation={cite} index={idx} />
                    ))}
                  </div>
                </div>
              )}

              {/* Assistant actions: Copy, Feedback */}
              {msg.role === "assistant" && (
                <div className="flex items-center justify-between border-t border-border/30 pt-1">
                  <span className="text-[10px] text-muted">{msg.createdAt}</span>
                  <FeedbackButtons messageId={msg.id} contentToCopy={msg.content} />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input Composer */}
      <div className="sticky bottom-4 w-full pt-4">
        <ChatComposer onSend={handleSend} />
      </div>
    </div>
  )
}
