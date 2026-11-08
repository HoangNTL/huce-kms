import { apiClient } from "@/lib/api-client"
import type { Conversation } from "../types"

export const chatService = {
  async getConversations(): Promise<Conversation[]> {
    return apiClient.get<Conversation[]>("/api/v1/chat/conversations")
  },

  async getConversation(id: string): Promise<Conversation> {
    return apiClient.get<Conversation>(`/api/v1/chat/conversations/${id}`)
  },

  async createConversation(title?: string): Promise<Conversation> {
    return apiClient.post<Conversation>("/api/v1/chat/conversations", { title })
  },

  async deleteConversation(id: string): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/api/v1/chat/conversations/${id}`)
  },

  async submitFeedback(
    messageId: string,
    feedback: "like" | "dislike"
  ): Promise<{ success: boolean }> {
    return apiClient.post<{ success: boolean }>(`/api/v1/chat/messages/${messageId}/feedback`, {
      feedback,
    })
  },
}
