"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Users,
  FileText,
  FolderTree,
  Globe,
  Plus,
  MessageSquare,
  History,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { useSidebarStore } from "@/stores/use-sidebar-store"
import { ROUTES } from "@/constants/routes"
import { cn } from "@/lib/utils"

const adminNavItems = [
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
    title: "Danh mục",
    href: ROUTES.ADMIN.CATEGORIES,
    icon: FolderTree,
  },
  {
    title: "Thu thập dữ liệu",
    href: ROUTES.ADMIN.CRAWLER,
    icon: Globe,
  },
]

const sampleThreads = [
  { id: "thread-1", title: "Quy định làm đồ án tốt nghiệp năm 2024" },
  { id: "thread-2", title: "Điều kiện xét học bổng khuyến khích" },
  { id: "thread-3", title: "Thủ tục xin cấp bảng điểm chính thức" },
]

export function AppSidebar() {
  const pathname = usePathname()
  const { isUserCollapsed, isAdminCollapsed } = useSidebarStore()

  const isAdminContext = pathname.startsWith("/admin")
  const isCollapsed = isAdminContext ? isAdminCollapsed : isUserCollapsed

  // Chat threads stored in localStorage for User context
  const [threads] = React.useState(() => {
    if (typeof window === "undefined") return sampleThreads
    try {
      const stored = localStorage.getItem("huce_recent_chat_threads")
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          const merged = [...parsed]
          for (const s of sampleThreads) {
            if (!merged.some((m) => m.id === s.id)) {
              merged.push(s)
            }
          }
          return merged.slice(0, 10)
        }
      }
    } catch {
      // Ignore
    }
    return sampleThreads
  })

  return (
    <aside
      className={cn(
        "flex h-full shrink-0 flex-col border-r border-border bg-surface/80 backdrop-blur-sm transition-[width] duration-300 ease-in-out",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {isAdminContext ? (
        /* --- ADMIN MODE NAVIGATION --- */
        <div className="flex flex-1 flex-col overflow-hidden">
          {!isCollapsed && (
            <div className="px-4 pt-3 pb-1 text-2xs font-semibold uppercase tracking-wider text-muted">
              Quản trị hệ thống
            </div>
          )}
          <nav className="flex-1 space-y-1 overflow-y-auto p-2">
            {adminNavItems.map((item) => {
            const Icon = item.icon
            const isActive =
              pathname === item.href ||
              (item.href !== ROUTES.ADMIN.DASHBOARD && pathname.startsWith(item.href))

            return (
              <Link
                key={item.href}
                href={item.href}
                title={item.title}
                className={cn(
                  "flex items-center rounded-lg transition-colors",
                  isCollapsed
                    ? "mx-auto h-10 w-10 justify-center"
                    : "gap-3 px-3 py-2.5 text-xs font-medium",
                  isActive
                    ? "bg-brand-primary font-semibold text-white shadow-xs"
                    : "text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!isCollapsed && <span className="truncate">{item.title}</span>}
              </Link>
            )
          })}
        </nav>
      </div>
      ) : (
        /* --- USER MODE: CHAT SESSIONS & HISTORY --- */
        <>
          {/* New chat action */}
          <div className="border-b border-border p-3">
            {isCollapsed ? (
              <Link href={ROUTES.USER.CHAT} className="flex justify-center">
                <Button
                  size="icon"
                  title="Đoạn chat mới"
                  aria-label="Đoạn chat mới"
                  className="h-10 w-10 rounded-xl bg-brand-primary text-white shadow-xs hover:bg-brand-primary-hover"
                >
                  <Plus className="h-5 w-5" />
                </Button>
              </Link>
            ) : (
              <Link href={ROUTES.USER.CHAT}>
                <Button className="w-full justify-start gap-2 bg-brand-primary text-white shadow-xs hover:bg-brand-primary-hover">
                  <Plus className="h-4 w-4" />
                  <span>Đoạn chat mới</span>
                </Button>
              </Link>
            )}
          </div>

          {/* History list */}
          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {!isCollapsed && (
              <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-semibold text-muted">
                <History className="h-3.5 w-3.5" />
                <span>Gần đây</span>
              </div>
            )}

            {threads.map((thread) => {
              const isActive = pathname === ROUTES.USER.CHAT_DETAIL(thread.id)
              return (
                <Link
                  key={thread.id}
                  href={ROUTES.USER.CHAT_DETAIL(thread.id)}
                  title={thread.title}
                  className={cn(
                    "flex items-center rounded-lg transition-colors",
                    isCollapsed
                      ? "mx-auto h-10 w-10 justify-center"
                      : "gap-2.5 px-3 py-2 text-xs font-medium",
                    isActive
                      ? "bg-brand-primary-subtle font-semibold text-brand-primary"
                      : "text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
                  )}
                >
                  <MessageSquare className="h-4 w-4 shrink-0 opacity-80" />
                  {!isCollapsed && <span className="truncate">{thread.title}</span>}
                </Link>
              )
            })}
          </div>
        </>
      )}
    </aside>
  )
}
