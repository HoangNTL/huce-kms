import * as React from "react"
import { AppSidebar } from "@/components/layout/app-sidebar"
import { AppHeader } from "@/components/layout/app-header"
import { AuthGuard } from "@/components/layout/auth-guard"

export default function UserLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen flex-col bg-background">
        <AppHeader />
        <div className="flex flex-1 overflow-hidden">
          <AppSidebar />
          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">{children}</main>
        </div>
      </div>
    </AuthGuard>
  )
}
