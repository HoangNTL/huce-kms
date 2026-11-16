"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { PanelLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { BrandLogo } from "@/components/layout/brand-logo"
import { UserDropdownMenu } from "@/components/layout/user-dropdown-menu"
import { useSidebarStore } from "@/stores/use-sidebar-store"
import { ROUTES } from "@/constants/routes"

export function AppHeader() {
  const pathname = usePathname()
  const { isUserCollapsed, isAdminCollapsed, toggleUserSidebar, toggleAdminSidebar } =
    useSidebarStore()

  const isAdminContext = pathname.startsWith("/admin")
  const isCollapsed = isAdminContext ? isAdminCollapsed : isUserCollapsed
  const toggle = isAdminContext ? toggleAdminSidebar : toggleUserSidebar

  const getBreadcrumb = () => {
    if (pathname.includes("/admin/users")) return "Người dùng"
    if (pathname.includes("/admin/documents/")) return "Chi tiết tài liệu"
    if (pathname.includes("/admin/documents")) return "Tài liệu"
    if (pathname.includes("/admin/crawler")) return "Thu thập dữ liệu"
    if (pathname.includes("/admin/profile") || pathname === "/profile") return "Tài khoản"
    return "Tổng quan"
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-surface/95 px-4 backdrop-blur-sm sm:px-6">
      {/* Left: Brand Identity & Toggle Controls */}
      <div className="flex items-center gap-2.5">
        <BrandLogo variant={isAdminContext ? "admin" : "user"} />

        <Separator orientation="vertical" className="mx-1 h-4" />

        <Button
          variant="ghost"
          size="icon"
          onClick={toggle}
          aria-label={isCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          title={isCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          className="h-8 w-8 text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        {/* Admin context breadcrumb */}
        {isAdminContext && (
          <>
            <Separator orientation="vertical" className="mx-1 hidden h-4 md:block" />
            <Breadcrumb className="hidden md:block">
              <BreadcrumbList className="text-xs">
                <BreadcrumbItem>
                  <BreadcrumbLink render={<Link href={ROUTES.ADMIN.DASHBOARD} />}>
                    Quản trị
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator />
                {pathname.includes("/admin/documents/") ? (
                  <>
                    <BreadcrumbItem>
                      <BreadcrumbLink render={<Link href={ROUTES.ADMIN.DOCUMENTS} />}>
                        Tài liệu
                      </BreadcrumbLink>
                    </BreadcrumbItem>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbPage className="font-medium text-heading">
                        Chi tiết
                      </BreadcrumbPage>
                    </BreadcrumbItem>
                  </>
                ) : (
                  <BreadcrumbItem>
                    <BreadcrumbPage className="font-medium text-heading">
                      {getBreadcrumb()}
                    </BreadcrumbPage>
                  </BreadcrumbItem>
                )}
              </BreadcrumbList>
            </Breadcrumb>
          </>
        )}
      </div>

      {/* Right: User Identity & Account Menu */}
      <div className="flex items-center gap-3">
        <UserDropdownMenu context={isAdminContext ? "admin" : "user"} />
      </div>
    </header>
  )
}
