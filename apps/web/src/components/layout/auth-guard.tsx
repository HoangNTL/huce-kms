"use client"

import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuthStore } from "@/stores/use-auth-store"
import { ROUTES } from "@/constants/routes"
import { USER_ROLES, type UserRole } from "@/types/user"

interface AuthGuardProps {
  children: React.ReactNode
  requiredRole?: UserRole
}

export function AuthGuard({ children, requiredRole }: AuthGuardProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isInitialized, user, initAuth } = useAuthStore()

  React.useEffect(() => {
    if (!isInitialized) {
      initAuth()
    }
  }, [isInitialized, initAuth])

  React.useEffect(() => {
    if (!isInitialized) return

    if (!isAuthenticated) {
      const fromQuery = pathname && pathname !== "/" ? `?from=${encodeURIComponent(pathname)}` : ""
      router.replace(`${ROUTES.AUTH.LOGIN}${fromQuery}`)
      return
    }

    if (requiredRole === USER_ROLES.ADMIN && user?.role !== USER_ROLES.ADMIN) {
      router.replace(ROUTES.USER.CHAT)
    }
  }, [isInitialized, isAuthenticated, user, requiredRole, router, pathname])

  // While checking silent session via HttpOnly cookie
  if (!isInitialized) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-3 border-brand-primary border-t-transparent" />
          <p className="text-xs font-medium text-muted">Đang kiểm tra phiên đăng nhập...</p>
        </div>
      </div>
    )
  }

  // Not authenticated or wrong role - prevent rendering children while redirecting
  if (!isAuthenticated) {
    return null
  }

  if (requiredRole === USER_ROLES.ADMIN && user?.role !== USER_ROLES.ADMIN) {
    return null
  }

  return <>{children}</>
}
