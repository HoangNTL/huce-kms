export interface Citation {
  documentId: string
  documentTitle: string
  chunkId: string
  snippet: string
  pageNumber?: number
  score?: number
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  citations?: Citation[]
  createdAt: string
  feedback?: "like" | "dislike"
}

export interface Conversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages?: ChatMessage[]
}

export interface SendMessagePayload {
  conversationId?: string
  message: string
}
