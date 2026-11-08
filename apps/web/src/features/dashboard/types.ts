export interface DashboardMetrics {
  totalDocuments: number
  totalChunks: number
  totalUsers: number
  totalConversations: number
  activeCrawlers: number
  indexedPercentage: number
}

export interface SystemHealth {
  apiStatus: "HEALTHY" | "DEGRADED" | "DOWN"
  databaseStatus: "CONNECTED" | "DISCONNECTED"
  vectorDbStatus: "CONNECTED" | "DISCONNECTED"
  uptimeSeconds: number
}
