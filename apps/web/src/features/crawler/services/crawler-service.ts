import { apiClient } from "@/lib/api-client"
import type { CrawlSource, CrawlJob } from "../types"
import type { PaginatedResponse, PaginationParams } from "@/types/api"

export const crawlerService = {
  async getSources(params?: PaginationParams): Promise<PaginatedResponse<CrawlSource>> {
    return apiClient.get<PaginatedResponse<CrawlSource>>("/api/v1/crawler/sources", { params })
  },

  async createSource(
    data: Omit<CrawlSource, "id" | "createdAt" | "lastCrawledAt">
  ): Promise<CrawlSource> {
    return apiClient.post<CrawlSource>("/api/v1/crawler/sources", data)
  },

  async deleteSource(id: string): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/api/v1/crawler/sources/${id}`)
  },

  async getJobs(params?: PaginationParams): Promise<PaginatedResponse<CrawlJob>> {
    return apiClient.get<PaginatedResponse<CrawlJob>>("/api/v1/crawler/jobs", { params })
  },

  async triggerJob(sourceId: string): Promise<CrawlJob> {
    return apiClient.post<CrawlJob>(`/api/v1/crawler/jobs/trigger`, { sourceId })
  },

  async stopJob(jobId: string): Promise<{ success: boolean }> {
    return apiClient.post<{ success: boolean }>(`/api/v1/crawler/jobs/${jobId}/stop`)
  },
}
