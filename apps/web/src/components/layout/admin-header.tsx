"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { MessageSquare, User, LogOut, PanelLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ROUTES } from "@/constants/routes"
import { useSidebarStore } from "@/stores/use-sidebar-store"

export function AdminHeader() {
  const pathname = usePathname()
  const { isAdminCollapsed, toggleAdminSidebar } = useSidebarStore()

  // Clean, concise breadcrumb structural labels
  const getBreadcrumb = () => {
    if (pathname.includes("/admin/users")) return "Người dùng"
    if (pathname.includes("/admin/documents/")) return "Chi tiết tài liệu"
    if (pathname.includes("/admin/documents")) return "Tài liệu"
    if (pathname.includes("/admin/crawler")) return "Crawler"
    if (pathname.includes("/admin/profile")) return "Hồ sơ cá nhân"
    return "Tổng quan"
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-surface/95 px-6 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleAdminSidebar}
          aria-label={isAdminCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          title={isAdminCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          className="h-8 w-8 text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <Separator orientation="vertical" className="mx-1 h-4" />

        <Breadcrumb>
          <BreadcrumbList className="text-xs">
            <BreadcrumbItem>
              <BreadcrumbLink render={<Link href={ROUTES.ADMIN.DASHBOARD} />}>
                Quản trị
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <BreadcrumbPage className="font-medium text-heading">
                {getBreadcrumb()}
              </BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div className="flex items-center gap-3">
        <Link href={ROUTES.USER.CHAT}>
          <Button variant="outline" size="sm" className="gap-1.5 text-xs">
            <MessageSquare className="h-3.5 w-3.5" />
            <span>Chuyển sang Chat AI</span>
          </Button>
        </Link>

        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button variant="ghost" size="icon" className="rounded-full" />}
          >
            <Avatar className="h-8 w-8 border border-border">
              <AvatarFallback className="bg-brand-primary text-xs font-medium text-white">
                AD
              </AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm leading-none font-medium text-heading">
                  Quản trị viên Hệ thống
                </p>
                <p className="text-xs leading-none text-muted">admin@huce.edu.vn</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              render={
                <Link
                  href={ROUTES.ADMIN.PROFILE}
                  className="flex cursor-pointer items-center gap-2"
                />
              }
            >
              <User className="h-4 w-4" />
              <span>Hồ sơ Admin</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              render={
                <Link
                  href={ROUTES.AUTH.LOGIN}
                  className="flex cursor-pointer items-center gap-2 text-destructive"
                />
              }
            >
              <LogOut className="h-4 w-4" />
              <span>Đăng xuất</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
