import { apiClient } from "@/lib/api-client"
import type { LoginPayload, RegisterPayload, AuthTokens } from "../types"
import type { UserProfile } from "@/types/user"

export const authService = {
  async login(payload: LoginPayload): Promise<AuthTokens> {
    const formData = new URLSearchParams()
    formData.append("username", payload.username)
    formData.append("password", payload.password)

    return apiClient.post<AuthTokens>("/api/v1/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
  },

  async register(payload: RegisterPayload): Promise<UserProfile> {
    return apiClient.post<UserProfile>("/api/v1/auth/register", payload)
  },

  async getMe(): Promise<UserProfile> {
    return apiClient.get<UserProfile>("/api/v1/users/me")
  },

  async logout(): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>("/api/v1/auth/logout")
  },
}
