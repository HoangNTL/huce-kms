import type { UserProfile, UserRole } from "@/types/user"

export type { UserProfile, UserRole }

export interface UpdateUserStatusPayload {
  is_active: boolean
}

export interface UpdateUserRolePayload {
  role: UserRole
}
