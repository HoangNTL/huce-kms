"use client"

import * as React from "react"
import Link from "next/link"
import { PanelLeft, Sparkles, User, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useSidebarStore } from "@/stores/use-sidebar-store"
import { ROUTES } from "@/constants/routes"

export function UserHeader() {
  const { isUserCollapsed, toggleUserSidebar } = useSidebarStore()

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-surface/95 px-4 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleUserSidebar}
          aria-label={isUserCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          title={isUserCollapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          className="h-8 w-8 text-body hover:bg-brand-primary-subtle hover:text-brand-primary"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>

        <Link
          href={ROUTES.USER.CHAT}
          className="flex items-center gap-2 font-semibold text-brand-primary"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-primary text-white">
            <Sparkles className="h-4 w-4" />
          </div>
          <span className="hidden font-heading text-sm font-bold tracking-tight text-heading sm:inline-block">
            HUCE KMS <span className="text-xs font-normal text-muted">Trợ lý AI</span>
          </span>
        </Link>
      </div>

      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button variant="ghost" size="icon" className="rounded-full" />}
          >
            <Avatar className="h-8 w-8 border border-border">
              <AvatarFallback className="bg-brand-primary/10 text-xs font-medium text-brand-primary">
                SV
              </AvatarFallback>
            </Avatar>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm leading-none font-medium text-heading">Sinh viên HUCE</p>
                <p className="text-xs leading-none text-muted">sinhvien@huce.edu.vn</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              render={
                <Link
                  href={ROUTES.USER.PROFILE}
                  className="flex cursor-pointer items-center gap-2"
                />
              }
            >
              <User className="h-4 w-4" />
              <span>Hồ sơ cá nhân</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              render={
                <Link
                  href={ROUTES.ADMIN.DASHBOARD}
                  className="flex cursor-pointer items-center gap-2"
                />
              }
            >
              <Sparkles className="h-4 w-4" />
              <span>Quản trị (Admin)</span>
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
