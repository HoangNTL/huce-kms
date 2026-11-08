import { apiClient } from "@/lib/api-client"
import type { DashboardMetrics, SystemHealth } from "../types"

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    return apiClient.get<DashboardMetrics>("/api/v1/dashboard/metrics")
  },

  async getHealth(): Promise<SystemHealth> {
    return apiClient.get<SystemHealth>("/api/v1/dashboard/health")
  },
}
