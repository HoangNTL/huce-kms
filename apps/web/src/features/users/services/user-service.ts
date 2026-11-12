import { apiClient } from "@/lib/api-client"
import { USER_ROLES } from "@/types/user"
import type { UserProfile, UpdateUserStatusPayload, UpdateUserRolePayload } from "../types"
import type { PaginatedResponse, PaginationParams } from "@/types/api"

export const userService = {
  async getUsers(params?: PaginationParams): Promise<PaginatedResponse<UserProfile>> {
    return apiClient.get<PaginatedResponse<UserProfile>>("/users", { params })
  },

  async getUser(id: string | number): Promise<UserProfile> {
    return apiClient.get<UserProfile>(`/users/${id}`)
  },

  async updateStatus(id: string | number, payload: UpdateUserStatusPayload): Promise<UserProfile> {
    return apiClient.patch<UserProfile>(`/users/${id}/status`, { is_active: payload.is_active })
  },

  async updateRole(id: string | number, payload: UpdateUserRolePayload): Promise<UserProfile> {
    const role = String(payload.role || USER_ROLES.USER).toLowerCase()
    return apiClient.patch<UserProfile>(`/users/${id}/role`, { role })
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },
}
