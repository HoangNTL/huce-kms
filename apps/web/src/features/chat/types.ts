export interface Citation {
  document_id: number | string
  title: string
  page_number: number
  chunk_index: number
  score: number
  snippet: string
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  citations?: Citation[]
  created_at: string
  feedback?: "like" | "dislike"
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
  messages?: ChatMessage[]
}

export interface SendMessagePayload {
  conversation_id?: string
  message: string
}
