import * as React from "react"
import Link from "next/link"
import { Sparkles } from "lucide-react"
import { ROUTES } from "@/constants/routes"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8">
      {/* Brand Header */}
      <div className="mb-6 flex flex-col items-center text-center">
        <Link href={ROUTES.HOME} className="mb-2 flex items-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-primary text-white shadow-xs">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="font-heading text-xl font-bold tracking-tight text-heading">
            HUCE KMS
          </span>
        </Link>
        <p className="max-w-sm text-xs text-muted">
          Trường Đại học Xây dựng Hà Nội • Hệ thống Quản trị Tri thức & Trợ lý AI
        </p>
      </div>

      {/* Auth Card Container */}
      <div className="w-full max-w-md">{children}</div>

      {/* Footer */}
      <div className="mt-8 text-center text-xs text-muted">
        <p>© {new Date().getFullYear()} Trường Đại học Xây dựng Hà Nội. Bảo lưu mọi quyền.</p>
      </div>
    </div>
  )
}
