import type { CategoryItem } from "@/features/categories"

export type { CategoryItem }

/**
 * FSM Ingestion States - Aligned with Backend DocumentStatus (SmallInteger / IntEnum):
 * 0 = UPLOADED, 1 = PENDING, 2 = PROCESSING, 3 = INDEXED, 4 = FAILED
 */
export enum DocumentStatus {
  UPLOADED = 0,
  PENDING = 1,
  PROCESSING = 2,
  INDEXED = 3,
  FAILED = 4,
}

/**
 * Document Origin - Aligned with Backend DocumentSourceType (SmallInteger / IntEnum):
 * 1 = UPLOAD, 2 = CRAWLER
 */
export enum DocumentSourceType {
  UPLOAD = 1,
  CRAWLER = 2,
}

export interface DocumentAsset {
  file_name: string
  file_type: string
  download_url: string
}

export interface DocumentMetadata {
  id: string
  title: string
  file_name: string
  file_path?: string
  file_size: number
  file_type: string
  file_hash?: string
  source_url?: string | null
  category?: string | CategoryItem | null
  category_id?: string | null
  status: DocumentStatus
  status_name?: string
  status_label?: string
  source_type?: DocumentSourceType
  source_type_name?: string
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
  context?: string | null
  metadata?: Record<string, unknown>
  token_count: number
  page_number: number
  page_start?: number
  page_end?: number
  content_hash?: string | null
  created_at?: string
}

export interface DocumentDetail extends DocumentMetadata {
  chunks?: DocumentChunk[]
  related_documents?: DocumentMetadata[]
  assets?: DocumentAsset[]
}
