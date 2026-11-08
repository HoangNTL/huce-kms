/**
 * User & Role Models
 */

export type UserRole = "USER" | "ADMIN"

export interface UserProfile {
  id: string
  username: string
  email: string
  fullName: string
  role: UserRole
  isActive: boolean
  createdAt: string
  updatedAt?: string
}

export interface UserTokenState {
  accessToken: string | null
  refreshToken: string | null
  user: UserProfile | null
}
