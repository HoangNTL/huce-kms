import { apiClient } from "@/lib/api-client"
import type { UserProfile, UpdateUserStatusPayload, UpdateUserRolePayload } from "../types"
import type { PaginatedResponse, PaginationParams } from "@/types/api"

export const userService = {
  async getUsers(params?: PaginationParams): Promise<PaginatedResponse<UserProfile>> {
    return apiClient.get<PaginatedResponse<UserProfile>>("/api/v1/users", { params })
  },

  async getUser(id: string): Promise<UserProfile> {
    return apiClient.get<UserProfile>(`/api/v1/users/${id}`)
  },

  async updateStatus(id: string, payload: UpdateUserStatusPayload): Promise<UserProfile> {
    return apiClient.put<UserProfile>(`/api/v1/users/${id}/status`, payload)
  },

  async updateRole(id: string, payload: UpdateUserRolePayload): Promise<UserProfile> {
    return apiClient.put<UserProfile>(`/api/v1/users/${id}/role`, payload)
  },
}
