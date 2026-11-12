import * as React from "react"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { AuthGuard } from "@/components/layout/auth-guard"
import { USER_ROLES } from "@/types/user"

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard requiredRole={USER_ROLES.ADMIN}>
      <div className="flex min-h-screen flex-col bg-background">
        <AppHeader />
        <div className="flex flex-1 overflow-hidden">
          <AppSidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto p-6">{children}</main>
        </div>
      </div>
    </AuthGuard>
  )
}
