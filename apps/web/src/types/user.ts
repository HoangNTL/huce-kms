/**
 * User & Role Models - Aligned with Backend FastAPI / SQLAlchemy Models
 */

/**
 * Standard User Roles in HUCE KMS.
 * Using 'as const' object pattern for optimal TypeScript type inference,
 * full tree-shaking, and seamless backend JSON string compatibility.
 */
export const USER_ROLES = {
  ADMIN: "admin",
  USER: "user",
} as const

export type UserRole = (typeof USER_ROLES)[keyof typeof USER_ROLES]

/**
 * Vietnamese display labels for User Roles
 */
export const ROLE_LABELS: Record<UserRole, string> = {
  [USER_ROLES.ADMIN]: "Quản trị viên",
  [USER_ROLES.USER]: "Người dùng",
}

export interface UserProfile {
  id: number | string
  username: string
  email: string
  full_name?: string | null
  role: UserRole
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface UserTokenState {
  access_token: string | null
  refresh_token: string | null
  user: UserProfile | null
}
