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
  id: string
  title: string
  file_name: string
  file_path?: string
  file_size: number
  file_type: string
  file_hash?: string
  category?: string | CategoryItem | null
  category_id?: string | null
  status: DocumentStatus
  chunk_count: number
  total_pages: number
  error_message?: string | null
  created_by_id?: string | null
  uploader_id?: string | null
  download_url?: string | null
  created_at: string
  updated_at?: string
  deleted_at?: string | null
}

export interface DocumentChunk {
  id: string
  document_id: string
  chunk_index: number
  content: string
  token_count: number
  page_number: number
  created_at?: string
}

export interface DocumentDetail extends DocumentMetadata {
  chunks?: DocumentChunk[]
}
