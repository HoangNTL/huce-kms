"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { User, LogOut, ShieldCheck, Sparkles, ChevronDown } from "lucide-react"
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
import { useAuthStore } from "@/stores/use-auth-store"
import { ROUTES } from "@/constants/routes"
import { USER_ROLES, ROLE_LABELS } from "@/types/user"

export interface UserDropdownMenuProps {
  context?: "admin" | "user"
}

export function UserDropdownMenu({ context = "user" }: UserDropdownMenuProps) {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  const handleLogout = async () => {
    await logout()
    router.push(ROUTES.AUTH.LOGIN)
  }

  const displayName = user?.full_name || user?.username || "Người dùng"
  const userInitials = (user?.username || (context === "admin" ? "AD" : "ND"))
    .slice(0, 2)
    .toUpperCase()
  const isAdmin = user?.role === USER_ROLES.ADMIN

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="ghost"
            className="flex h-auto items-center gap-2.5 rounded-lg border border-transparent px-2 py-1 transition-all hover:border-border/60 hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-brand-primary"
            aria-label="Menu tài khoản người dùng"
          />
        }
      >
        <Avatar className="h-8 w-8 cursor-pointer border border-border shadow-xs">
          <AvatarFallback className="bg-brand-primary text-xs font-semibold text-white">
            {userInitials}
          </AvatarFallback>
        </Avatar>

        {/* User Identity Pill */}
        <div className="hidden text-left sm:flex sm:flex-col">
          <span className="max-w-[140px] truncate text-xs font-semibold leading-tight text-heading">
            {displayName}
          </span>
          <span className="text-[11px] leading-tight text-muted">
            {user?.role ? ROLE_LABELS[user.role] : "Người dùng"}
          </span>
        </div>

        <ChevronDown className="hidden h-3.5 w-3.5 text-muted sm:block" />
      </DropdownMenuTrigger>

      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal py-1.5">
          <p className="truncate text-xs text-muted">
            {user?.email || user?.username}
          </p>
        </DropdownMenuLabel>

        <DropdownMenuSeparator />

        {/* Profile Link */}
        <DropdownMenuItem
          render={
            <Link
              href={context === "admin" ? ROUTES.ADMIN.PROFILE : ROUTES.USER.PROFILE}
              className="flex cursor-pointer items-center gap-2"
            />
          }
        >
          <User className="h-4 w-4 text-muted" />
          <span>Hồ sơ tài khoản</span>
        </DropdownMenuItem>

        {/* Context switch (Single clean location - no header duplication) */}
        {isAdmin && context === "admin" && (
          <DropdownMenuItem
            render={
              <Link
                href={ROUTES.USER.CHAT}
                className="flex cursor-pointer items-center gap-2"
              />
            }
          >
            <Sparkles className="h-4 w-4 text-brand-primary" />
            <span>Chat AI</span>
          </DropdownMenuItem>
        )}

        {isAdmin && context === "user" && (
          <DropdownMenuItem
            render={
              <Link
                href={ROUTES.ADMIN.DASHBOARD}
                className="flex cursor-pointer items-center gap-2"
              />
            }
          >
            <ShieldCheck className="h-4 w-4 text-brand-primary" />
            <span>Quản trị hệ thống</span>
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        {/* Logout */}
        <DropdownMenuItem
          variant="destructive"
          onClick={handleLogout}
          className="flex cursor-pointer items-center gap-2 text-destructive hover:bg-destructive/10 hover:text-destructive focus:bg-destructive/10 focus:text-destructive [&>svg]:text-destructive! [&>span]:text-destructive!"
        >
          <LogOut className="h-4 w-4" />
          <span>Đăng xuất</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
