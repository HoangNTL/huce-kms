/**
 * User & Role Models - Aligned with Backend FastAPI / SQLAlchemy Models
 * Role mapping: 1 = USER (Standard user), 2 = ADMIN (Administrator)
 */

export enum UserRole {
  USER = 1,
  ADMIN = 2,
}

export const USER_ROLE_CONFIG: Record<
  UserRole,
  { label: string; codeName: string; badgeVariant: "default" | "secondary" }
> = {
  [UserRole.USER]: {
    label: "Người dùng",
    codeName: "user",
    badgeVariant: "secondary",
  },
  [UserRole.ADMIN]: {
    label: "Quản trị viên",
    codeName: "admin",
    badgeVariant: "default",
  },
}

export const ROLE_LABELS: Record<string | number, string> = {
  [UserRole.USER]: "Người dùng",
  [UserRole.ADMIN]: "Quản trị viên",
  user: "Người dùng",
  admin: "Quản trị viên",
}

export const isUserAdmin = (role?: UserRole | number | string | null): boolean => {
  if (role == null) return false
  return role === UserRole.ADMIN || role === 2 || String(role).toLowerCase() === "admin"
}

export interface UserProfile {
  id: number | string
  username: string
  email: string
  full_name?: string | null
  role: UserRole
  role_name?: string
  role_label?: string
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface UserTokenState {
  access_token: string | null
  refresh_token: string | null
  user: UserProfile | null
}
