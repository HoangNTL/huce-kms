"use client"

import * as React from "react"
import type { ChatMessage, Citation } from "../types"
import { useAuthStore } from "@/stores/use-auth-store"
import { toast } from "@/components/ui/sonner"
import { API_BASE_URL } from "@/config/env"
import { silentRefreshToken } from "@/lib/api-client"

export function useRAGStream(threadId: string) {
  const [messages, setMessages] = React.useState<ChatMessage[]>(() => {
    if (typeof window === "undefined") return []
    try {
      const stored = localStorage.getItem(`huce_chat_thread_${threadId}`)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed
        }
      }
    } catch {
      // Ignore storage read error
    }
    return []
  })
  const [isLoading, setIsLoading] = React.useState(false)

  // Save messages to local storage whenever they change
  const saveMessages = React.useCallback(
    (newMessages: ChatMessage[]) => {
      setMessages(newMessages)
      try {
        localStorage.setItem(`huce_chat_thread_${threadId}`, JSON.stringify(newMessages))
        
        // Also update recent threads list
        const recentThreadsKey = "huce_recent_chat_threads"
        const existing = localStorage.getItem(recentThreadsKey)
        let list: Array<{ id: string; title: string; updatedAt: string }> = existing ? JSON.parse(existing) : []
        
        const firstUserMsg = newMessages.find((m) => m.role === "user")
        const title = firstUserMsg ? firstUserMsg.content.slice(0, 50) : `Phiên hỏi đáp #${threadId}`
        
        list = list.filter((item) => item.id !== threadId)
        list.unshift({ id: threadId, title, updatedAt: new Date().toISOString() })
        localStorage.setItem(recentThreadsKey, JSON.stringify(list.slice(0, 10)))
      } catch {
        // Ignore storage write error
      }
    },
    [threadId]
  )

  const sendMessage = React.useCallback(
    async (query: string, categoryId?: number) => {
      const trimmed = query.trim()
      if (!trimmed || isLoading) return

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: trimmed,
        created_at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }

      const assistantMsgId = `assistant-${Date.now()}`
      const assistantMsg: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
        citations: [],
        created_at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      }

      const updated = [...messages, userMsg, assistantMsg]
      setMessages(updated)
      setIsLoading(true)

      const streamEndpoint = `${API_BASE_URL}/rag/stream`
      const activeToken = useAuthStore.getState().accessToken

      const buildHeaders = (t: string | null) => ({
        "Content-Type": "application/json",
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      })

      const reqBody = JSON.stringify({
        query: trimmed,
        category_id: categoryId || null,
        top_k: 5,
        temperature: 0.3,
      })

      try {
        let response = await fetch(streamEndpoint, {
          method: "POST",
          credentials: "include",
          headers: buildHeaders(activeToken),
          body: reqBody,
        })

        // If access token expired, attempt silent refresh via HttpOnly cookie and retry once
        if (response.status === 401) {
          const renewedToken = await silentRefreshToken()
          if (renewedToken) {
            response = await fetch(streamEndpoint, {
              method: "POST",
              credentials: "include",
              headers: buildHeaders(renewedToken),
              body: reqBody,
            })
          }
        }

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}))
          throw new Error(errData.message || errData.detail || `Server responded with ${response.status}`)
        }

        if (!response.body) {
          throw new Error("No response body received from server")
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder("utf-8")
        let streamedContent = ""
        let citations: Citation[] = []
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n\n")
          buffer = lines.pop() || ""

          for (const line of lines) {
            const trimmedLine = line.trim()
            if (!trimmedLine.startsWith("data:")) continue

            const dataContent = trimmedLine.replace(/^data:\s*/, "")
            if (dataContent === "[DONE]") {
              continue
            }

            try {
              const parsed = JSON.parse(dataContent)
              if (parsed.type === "token") {
                streamedContent += parsed.content || ""
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, content: streamedContent } : m
                  )
                )
              } else if (parsed.type === "sources") {
                citations = parsed.sources || []
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId ? { ...m, citations } : m
                  )
                )
              } else if (parsed.type === "error") {
                toast.error("Lỗi tạo câu trả lời", {
                  description: parsed.message,
                })
              }
            } catch {
              // Ignore malformed JSON in SSE chunk
            }
          }
        }

        // Finalize state and save to local storage
        const finalized = updated.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content:
                  streamedContent ||
                  "Hệ thống không tìm thấy tài liệu phù hợp để trả lời câu hỏi của bạn.",
                citations,
              }
            : m
        )
        saveMessages(finalized)
      } catch (err) {
        console.error("RAG stream error:", err)
        const errorMessage = err instanceof Error ? err.message : "Lỗi kết nối máy chủ AI"
        toast.error("Không thể hoàn thành câu trả lời", {
          description: errorMessage,
        })
        const finalized = updated.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: `Rất tiếc, đã xảy ra lỗi trong quá trình xử lý câu hỏi: ${errorMessage}. Vui lòng thử lại sau.`,
              }
            : m
        )
        saveMessages(finalized)
      } finally {
        setIsLoading(false)
      }
    },
    [messages, isLoading, saveMessages]
  )

  const clearMessages = React.useCallback(() => {
    setMessages([])
    try {
      localStorage.removeItem(`huce_chat_thread_${threadId}`)
    } catch {
      // Ignore
    }
  }, [threadId])

  return {
    messages,
    isLoading,
    sendMessage,
    clearMessages,
  }
}
