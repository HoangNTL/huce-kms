import type { UserProfile, UserRole } from "@/types/user"

export type { UserProfile, UserRole }

export interface UpdateUserStatusPayload {
  isActive: boolean
}

export interface UpdateUserRolePayload {
  role: UserRole
}
