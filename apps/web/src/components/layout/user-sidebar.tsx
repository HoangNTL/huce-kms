"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Plus, MessageSquare, History } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useSidebarStore } from "@/stores/use-sidebar-store"
import { ROUTES } from "@/constants/routes"
import { cn } from "@/lib/utils"

// Sample conversations
const sampleThreads = [
  { id: "thread-1", title: "Quy định làm đồ án tốt nghiệp năm 2024" },
  { id: "thread-2", title: "Điều kiện xét học bổng khuyến khích" },
  { id: "thread-3", title: "Thủ tục xin cấp bảng điểm chính thức" },
]

export function UserSidebar() {
  const { isUserCollapsed } = useSidebarStore()
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        "sticky top-14 flex h-[calc(100vh-3.5rem)] shrink-0 flex-col border-r border-border bg-surface/80 backdrop-blur-sm transition-[width] duration-300 ease-in-out",
        isUserCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* New chat action */}
      <div className="border-b border-border p-3">
        {isUserCollapsed ? (
          <Link href={ROUTES.USER.CHAT} className="flex justify-center">
            <Button
              size="icon"
              title="Đoạn chat mới"
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

      {/* History section */}
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {!isUserCollapsed && (
          <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-semibold text-muted">
            <History className="h-3.5 w-3.5" />
            <span>Gần đây</span>
          </div>
        )}

        {sampleThreads.map((thread) => {
          const isActive = pathname === ROUTES.USER.CHAT_DETAIL(thread.id)
          return (
            <Link
              key={thread.id}
              href={ROUTES.USER.CHAT_DETAIL(thread.id)}
              title={thread.title}
              className={cn(
                "flex items-center rounded-lg transition-colors",
                isUserCollapsed
                  ? "mx-auto h-10 w-10 justify-center"
                  : "gap-2.5 px-3 py-2 text-xs font-medium",
                isActive
                  ? "bg-brand-primary-subtle font-semibold text-brand-primary"
                  : "text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
              )}
            >
              <MessageSquare className="h-4 w-4 shrink-0 opacity-80" />
              {!isUserCollapsed && <span className="truncate">{thread.title}</span>}
            </Link>
          )
        })}
      </div>
    </aside>
  )
}
