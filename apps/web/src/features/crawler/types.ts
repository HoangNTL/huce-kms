export interface CrawlSource {
  id: string
  name: string
  url: string
  crawl_depth: number
  schedule_cron?: string
  is_active: boolean
  last_crawled_at?: string
  created_at: string
}

export type CrawlJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "PAUSED"

export interface CrawlJob {
  id: string
  source_id: string
  source_name: string
  status: CrawlJobStatus
  pages_crawled: number
  documents_found: number
  started_at: string
  finished_at?: string
  error_message?: string
}

export interface CrawlDirectPayload {
  url: string
  auto_ingest?: boolean
  auto_publish?: boolean
  category_id?: string
}

export interface CrawlDirectResult {
  url: string
  status: string
  title?: string
  content_length: number
  media_count: number
  page_dir?: string
  error_message?: string
  ingested: boolean
  published?: boolean
}

export interface DiscoverPayload {
  url: string
  max_items?: number
}

export interface DiscoveredItem {
  url: string
  title?: string
  published_at?: string
  status?: string
}

export interface DiscoverResult {
  source_url: string
  source_type: string
  total_discovered: number
  items: DiscoveredItem[]
  queue_file?: string
}

export interface DiscoveredFileSummary {
  filename: string
  source_url?: string
  total: number
  created_at: number
}

export interface QueueResponse {
  discovered_files: DiscoveredFileSummary[]
  approved_total: number
  approved_urls: string[]
}

export interface ApproveQueuePayload {
  queue_file?: string
  approved_urls?: string[]
  approve_all?: boolean
}

export interface IngestPayload {
  session_id?: string
  page_hash?: string
  category_id?: string
  auto_publish?: boolean
}

export interface QueueItem {
  url: string
  title?: string
  published_at?: string
  status: "discovered" | "approved" | "rejected" | "crawled"
}

export interface QueueFileSummary {
  file_name: string
  modified_at: string
  total_urls: number
  pending_urls: number
}

export interface CrawlSessionSummary {
  session_id: string
  started_at: string
  finished_at?: string
  status: string
  total_urls: number
  succeeded: number
  failed: number
}

export interface StartQueuePayload {
  auto_ingest?: boolean
  auto_publish?: boolean
  category_id?: string
  max_concurrency?: number
  clear_queue?: boolean
}

export interface StartQueueResponse {
  session_id: string
  status: string
  total_urls: number
  message?: string
}

export interface StartQueueResult {
  session_id: string
  total: number
  successful: number
  failed: number
  duration_seconds: number
  ingest_summary?: {
    total_pages: number
    total_documents: number
    successful: number
    skipped: number
    failed: number
  }
}

export interface SessionDetailMedia {
  name: string
  size: number
  url?: string
}

export interface SessionDetailItem {
  url: string
  title: string
  status: string
  page_hash?: string
  duration_seconds?: number
  pdf_count: number
  image_count: number
  pdfs: SessionDetailMedia[]
  images: SessionDetailMedia[]
  markdown_content?: string
  markdown_length: number
  is_meaningful_markdown: boolean
  has_ocr: boolean
  is_ingested?: boolean
  ingested_at?: string | null
  errors: string[]
}

export interface SessionDetailData {
  session: Record<string, unknown>
  items: SessionDetailItem[]
}
