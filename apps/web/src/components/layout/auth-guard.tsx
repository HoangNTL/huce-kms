"use client"

import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuthStore } from "@/stores/use-auth-store"
import { ROUTES } from "@/constants/routes"
import { USER_ROLES, type UserRole } from "@/types/user"
import { LoadingSpinner } from "@/components/shared/loading-spinner"

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
      <LoadingSpinner
        fullScreen
        orientation="vertical"
        size="lg"
        label="Đang kiểm tra phiên đăng nhập..."
      />
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
