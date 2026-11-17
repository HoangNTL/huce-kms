import type { CategoryItem } from "@/features/categories"

export type { CategoryItem }

export type DocumentStatus =
  | "pending"
  | "processing"
  | "indexed"
  | "failed"
  | "UPLOADED"
  | "PROCESSING"
  | "INDEXED"
  | "FAILED"

export interface DocumentMetadata {
  id: string | number
  title: string
  file_name: string
  file_path?: string
  file_size: number
  file_type: string
  file_hash?: string
  category?: string | CategoryItem | null
  category_id?: number | null
  status: DocumentStatus
  chunk_count: number
  total_pages: number
  error_message?: string | null
  uploader_id?: number | null
  download_url?: string | null
  created_at: string
  updated_at?: string
}

export interface DocumentChunk {
  id: string
  document_id: string | number
  chunk_index: number
  content: string
  token_count: number
  page_number: number
  created_at?: string
}

export interface DocumentDetail extends DocumentMetadata {
  chunks?: DocumentChunk[]
}
