"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, Users, FileText, Globe, ShieldCheck, LogOut } from "lucide-react"
import { ROUTES } from "@/constants/routes"
import { useSidebarStore } from "@/stores/use-sidebar-store"
import { cn } from "@/lib/utils"

const navItems = [
  {
    title: "Dashboard",
    href: ROUTES.ADMIN.DASHBOARD,
    icon: LayoutDashboard,
  },
  {
    title: "Người dùng",
    href: ROUTES.ADMIN.USERS,
    icon: Users,
  },
  {
    title: "Tài liệu",
    href: ROUTES.ADMIN.DOCUMENTS,
    icon: FileText,
  },
  {
    title: "Crawler",
    href: ROUTES.ADMIN.CRAWLER,
    icon: Globe,
  },
]

export function AdminSidebar() {
  const pathname = usePathname()
  const { isAdminCollapsed } = useSidebarStore()

  return (
    <aside
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-300 ease-in-out",
        isAdminCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Brand Header */}
      <div
        className={cn(
          "flex h-14 items-center border-b border-border transition-all",
          isAdminCollapsed ? "justify-center px-2" : "gap-2.5 px-4"
        )}
      >
        <Link
          href={ROUTES.ADMIN.DASHBOARD}
          title="HUCE KMS - Quản trị hệ thống"
          className={cn(
            "flex items-center overflow-hidden",
            isAdminCollapsed ? "justify-center" : "gap-2.5"
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-primary text-white shadow-xs">
            <ShieldCheck className="h-4 w-4" />
          </div>
          {!isAdminCollapsed && (
            <div className="overflow-hidden">
              <p className="truncate font-heading text-sm leading-tight font-bold text-heading">
                HUCE KMS
              </p>
              <p className="truncate text-[10px] font-semibold tracking-wider text-brand-primary uppercase">
                Quản trị hệ thống
              </p>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1.5 overflow-y-auto p-2">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== ROUTES.ADMIN.DASHBOARD && pathname.startsWith(item.href))
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.title}
              className={cn(
                "flex items-center rounded-lg transition-colors",
                isAdminCollapsed
                  ? "mx-auto h-10 w-10 justify-center"
                  : "gap-3 px-3 py-2.5 text-xs font-medium",
                isActive
                  ? "bg-brand-primary font-semibold text-white shadow-xs"
                  : "text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!isAdminCollapsed && <span className="truncate">{item.title}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Footer: Logout */}
      <div className="border-t border-border p-2">
        <Link
          href={ROUTES.AUTH.LOGIN}
          title="Đăng xuất"
          className={cn(
            "flex items-center rounded-lg text-xs font-medium text-destructive transition-colors hover:bg-destructive/10",
            isAdminCollapsed ? "mx-auto h-10 w-10 justify-center" : "gap-3 px-3 py-2"
          )}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!isAdminCollapsed && <span>Đăng xuất</span>}
        </Link>
      </div>
    </aside>
  )
}
