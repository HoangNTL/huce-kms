import { apiClient } from "@/lib/api-client"
import type { LoginPayload, RegisterPayload, AuthTokens } from "../types"
import type { UserProfile } from "@/types/user"

export const authService = {
  async login(payload: LoginPayload): Promise<AuthTokens> {
    return apiClient.post<AuthTokens>("/auth/login", payload)
  },

  async register(payload: RegisterPayload): Promise<UserProfile> {
    const backendPayload = {
      username: payload.username,
      email: payload.email,
      full_name: payload.full_name || null,
      password: payload.password,
    }
    return apiClient.post<UserProfile>("/auth/register", backendPayload)
  },

  async getMe(): Promise<UserProfile> {
    return apiClient.get<UserProfile>("/auth/me")
  },

  async refreshToken(): Promise<AuthTokens> {
    return apiClient.post<AuthTokens>("/auth/refresh")
  },

  async logout(): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>("/auth/logout")
  },
}
