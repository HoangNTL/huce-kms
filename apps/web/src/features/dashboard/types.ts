export interface ServiceStatus {
  name: string
  status: "healthy" | "degraded" | "down" | string
  latency_ms?: number
  details?: string
}

export interface DashboardStats {
  total_documents: number
  total_chunks: number
  total_users: number
  active_users: number
  total_categories: number
  total_file_size_bytes?: number
  indexed_documents?: number
  services: ServiceStatus[]
}
