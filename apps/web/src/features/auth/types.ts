import type { UserProfile } from "@/types/user"

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  full_name: string
  password: string
}

export interface AuthTokens {
  access_token: string
  refresh_token?: string | null
  token_type?: string
  user: UserProfile
}
