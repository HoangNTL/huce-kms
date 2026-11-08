export interface CrawlSource {
  id: string
  name: string
  url: string
  crawlDepth: number
  scheduleCron?: string
  isActive: boolean
  lastCrawledAt?: string
  createdAt: string
}

export type CrawlJobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "PAUSED"

export interface CrawlJob {
  id: string
  sourceId: string
  sourceName: string
  status: CrawlJobStatus
  pagesCrawled: number
  documentsFound: number
  startedAt: string
  finishedAt?: string
  errorMessage?: string
}
