import { apiClient } from "@/lib/api-client"
import type {
  CrawlDirectPayload,
  CrawlDirectResult,
  DiscoverPayload,
  DiscoverResult,
  QueueResponse,
  ApproveQueuePayload,
  IngestPayload,
} from "../types"

export const crawlerService = {
  async crawlDirect(payload: CrawlDirectPayload): Promise<CrawlDirectResult> {
    return apiClient.post<CrawlDirectResult>("/crawler/crawl", payload)
  },

  async discover(payload: DiscoverPayload): Promise<DiscoverResult> {
    return apiClient.post<DiscoverResult>("/crawler/discover", payload)
  },

  async getQueue(): Promise<QueueResponse> {
    return apiClient.get<QueueResponse>("/crawler/queue")
  },

  async approveQueue(payload: ApproveQueuePayload): Promise<{
    approved_file: string
    total_approved: number
    urls: string[]
  }> {
    return apiClient.post<{ approved_file: string; total_approved: number; urls: string[] }>(
      "/crawler/queue/approve",
      payload
    )
  },

  async ingest(payload: IngestPayload): Promise<Record<string, unknown>> {
    return apiClient.post<Record<string, unknown>>("/crawler/ingest", payload)
  },

  async getSessions(): Promise<Array<Record<string, unknown>>> {
    return apiClient.get<Array<Record<string, unknown>>>("/crawler/sessions")
  },
}
