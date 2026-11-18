"use client"

import * as React from "react"
import { ThumbsUp, ThumbsDown, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { toast } from "@/components/ui/sonner"
import { cn } from "@/lib/utils"

interface FeedbackButtonsProps {
  messageId: string
  contentToCopy: string
  initialFeedback?: "like" | "dislike"
  onFeedback?: (messageId: string, type: "like" | "dislike") => void
  className?: string
}

export function FeedbackButtons({
  messageId,
  contentToCopy,
  initialFeedback,
  onFeedback,
  className,
}: FeedbackButtonsProps) {
  const [feedback, setFeedback] = React.useState<"like" | "dislike" | undefined>(initialFeedback)
  const [copied, setCopied] = React.useState(false)

  const handleFeedback = (type: "like" | "dislike") => {
    const next = feedback === type ? undefined : type
    setFeedback(next)
    if (next && onFeedback) {
      onFeedback(messageId, next)
    }
    if (next === "like") {
      toast.success("Cảm ơn đánh giá tích cực của bạn!")
    } else if (next === "dislike") {
      toast.info("Ghi nhận phản hồi để cải thiện chất lượng câu trả lời.")
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(contentToCopy)
      setCopied(true)
      toast.success("Đã sao chép câu trả lời vào clipboard")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("Không thể sao chép văn bản")
    }
  }

  return (
    <div className={cn("flex items-center gap-1 text-muted", className)}>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 text-muted hover:text-heading"
        onClick={handleCopy}
        title="Sao chép câu trả lời"
        aria-label="Sao chép câu trả lời"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
      </Button>

      <Button
        variant="ghost"
        size="icon"
        className={cn(
          "h-7 w-7",
          feedback === "like"
            ? "bg-brand-primary-subtle text-brand-primary"
            : "text-muted hover:text-heading"
        )}
        onClick={() => handleFeedback("like")}
        title="Hữu ích"
        aria-label="Đánh giá hữu ích"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </Button>

      <Button
        variant="ghost"
        size="icon"
        className={cn(
          "h-7 w-7",
          feedback === "dislike"
            ? "bg-destructive/10 text-destructive"
            : "text-muted hover:text-heading"
        )}
        onClick={() => handleFeedback("dislike")}
        title="Chưa chính xác"
        aria-label="Đánh giá chưa chính xác"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}
