import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { ROUTES } from "@/constants/routes"
import { cn } from "@/lib/utils"

export interface BrandLogoProps {
  variant?: "admin" | "user" | "auth"
  href?: string
  collapsed?: boolean
  className?: string
}

export function BrandLogo({
  variant = "user",
  href,
  collapsed = false,
  className,
}: BrandLogoProps) {
  const defaultHref =
    variant === "admin"
      ? ROUTES.ADMIN.DASHBOARD
      : variant === "user"
        ? ROUTES.USER.CHAT
        : ROUTES.HOME

  const targetHref = href ?? defaultHref

  if (variant === "auth") {
    return (
      <Link
        href={targetHref}
        className={cn(
          "flex items-center gap-3 transition-opacity hover:opacity-90",
          className
        )}
      >
        <Image
          src="/huce-logo.svg"
          alt="HUCE Logo"
          width={44}
          height={44}
          className="h-11 w-11 shrink-0 object-contain"
          priority
        />
        <div className="flex flex-col text-left">
          <span className="font-heading text-xl font-bold tracking-tight text-heading leading-tight">
            HUCE KMS
          </span>
          <span className="text-xs text-muted leading-tight">
            Quản trị Tri thức và Trợ lý AI
          </span>
        </div>
      </Link>
    )
  }

  const badgeText = variant === "admin" ? "Admin" : "Trợ lý AI"

  return (
    <Link
      href={targetHref}
      title={variant === "admin" ? "HUCE KMS - Quản trị hệ thống" : "HUCE KMS - Trợ lý AI"}
      className={cn(
        "flex items-center gap-2.5 transition-opacity hover:opacity-90",
        collapsed && "justify-center",
        className
      )}
    >
      <Image
        src="/huce-logo.svg"
        alt="HUCE Logo"
        width={32}
        height={32}
        className="h-8 w-8 shrink-0 object-contain"
        priority
      />
      {!collapsed && (
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="truncate font-heading text-sm font-bold tracking-tight text-heading">
            HUCE KMS
          </span>
          <span className="rounded-md bg-brand-primary-subtle px-1.5 py-0.5 text-[10px] font-semibold text-brand-primary">
            {badgeText}
          </span>
        </div>
      )}
    </Link>
  )
}
