import * as React from "react"
import { BrandLogo } from "@/components/layout/brand-logo"

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8">
      {/* Brand Header */}
      <div className="mb-6 flex justify-center">
        <BrandLogo variant="auth" />
      </div>

      {/* Auth Card Container */}
      <div className="w-full max-w-md">{children}</div>

      {/* Footer */}
      <div className="mt-8 text-center text-xs text-muted">
        <p>© {new Date().getFullYear()} Trường Đại học Xây dựng Hà Nội</p>
      </div>
    </div>
  )
}
