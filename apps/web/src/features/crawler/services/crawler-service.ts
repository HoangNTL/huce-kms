import { apiClient } from "@/lib/api-client"
import { API_BASE_URL } from "@/config/env"
import type {
  CrawlDirectPayload,
  CrawlDirectResult,
  DiscoverPayload,
  DiscoverResult,
  QueueResponse,
  ApproveQueuePayload,
  IngestPayload,
  StartQueuePayload,
  StartQueueResponse,
  SessionDetailData,
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

  async startQueue(payload: StartQueuePayload = {}): Promise<StartQueueResponse> {
    return apiClient.post<StartQueueResponse>("/crawler/queue/start", payload)
  },

  async cancelSession(sessionId: string): Promise<{ session_id: string; status: string }> {
    return apiClient.post<{ session_id: string; status: string }>(`/crawler/sessions/${sessionId}/cancel`)
  },

  async clearQueue(): Promise<{ approved_total: number; approved_urls: string[] }> {
    return apiClient.delete<{ approved_total: number; approved_urls: string[] }>("/crawler/queue")
  },

  async removeQueueItem(url: string): Promise<{ approved_total: number; approved_urls: string[] }> {
    return apiClient.delete<{ approved_total: number; approved_urls: string[] }>("/crawler/queue/item", {
      params: { url },
    })
  },

  async ingest(payload: IngestPayload): Promise<Record<string, unknown>> {
    return apiClient.post<Record<string, unknown>>("/crawler/ingest", payload)
  },

  async getSessions(): Promise<Array<Record<string, unknown>>> {
    return apiClient.get<Array<Record<string, unknown>>>("/crawler/sessions")
  },

  async getSessionDetails(sessionId: string): Promise<SessionDetailData> {
    return apiClient.get<SessionDetailData>(`/crawler/sessions/${sessionId}`)
  },

  getMediaUrl(mediaPath?: string): string {
    if (!mediaPath) return ""
    if (mediaPath.startsWith("http")) return mediaPath
    const base = API_BASE_URL.replace(/\/api\/v1\/?$/, "")
    const normalized = mediaPath.startsWith("/") ? mediaPath : `/${mediaPath}`
    return `${base}${normalized}`
  },
}

