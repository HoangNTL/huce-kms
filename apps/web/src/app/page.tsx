"use client"

import * as React from "react"
import Link from "next/link"
import Image from "next/image"
import { MessageSquare, FileText, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ROUTES } from "@/constants/routes"

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col justify-between bg-background">
      {/* Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          {/* Brand Identity with Official HUCE Logo */}
          <Link href="/" className="flex items-center gap-3 transition-opacity hover:opacity-90">
            <Image
              src="/huce-logo.svg"
              alt="HUCE Logo"
              width={36}
              height={36}
              className="h-9 w-9 shrink-0 object-contain"
              priority
            />
            <div className="flex flex-col text-left">
              <span className="font-heading text-base font-bold leading-tight text-heading">
                HUCE KMS
              </span>
              <span className="text-[11px] leading-tight text-muted">
                Đại học Xây dựng Hà Nội
              </span>
            </div>
          </Link>

          {/* Navigation Actions (Clean & concise: no duplicate Chat AI button) */}
          <div className="flex items-center gap-2">
            <Link href={ROUTES.AUTH.LOGIN}>
              <Button variant="ghost" size="sm" className="text-xs">
                Đăng nhập
              </Button>
            </Link>
            <Link href={ROUTES.AUTH.REGISTER}>
              <Button size="sm" className="bg-brand-primary text-xs text-white hover:bg-brand-primary-hover">
                Đăng ký
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="mx-auto flex max-w-4xl flex-1 flex-col items-center justify-center space-y-6 px-4 py-16 text-center sm:px-6">
        <h1 className="font-heading text-3xl font-extrabold tracking-tight text-heading sm:text-5xl leading-tight">
          Hệ thống Quản trị Tri thức và Trợ lý AI{" "}
          <span className="text-brand-primary">HUCE</span>
        </h1>

        <p className="max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
          Tra cứu tức thì quy chế đào tạo, thủ tục học vụ và hỏi đáp thông minh với nguồn trích dẫn đối chứng minh bạch từ Đại học Xây dựng Hà Nội.
        </p>

        {/* Action Buttons (Streamlined & icon-free) */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-3">
          <Link href={ROUTES.USER.CHAT}>
            <Button
              size="lg"
              className="bg-brand-primary px-6 text-white shadow-xs hover:bg-brand-primary-hover font-semibold"
            >
              Trò chuyện với AI
            </Button>
          </Link>
          <Link href={ROUTES.ADMIN.DASHBOARD}>
            <Button size="lg" variant="outline" className="border-border px-6 font-medium">
              Trang quản trị
            </Button>
          </Link>
        </div>

        {/* 3 Intuitive Benefit Showcase Cards */}
        <div className="grid w-full grid-cols-1 gap-4 pt-12 text-left sm:grid-cols-3">
          <Link href={ROUTES.USER.CHAT}>
            <Card className="h-full cursor-pointer border-border shadow-xs transition-all hover:border-brand-primary/50 hover:bg-brand-primary/5">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <CardTitle className="text-base font-bold text-heading">Hỏi đáp Trợ lý AI</CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  Giải đáp mọi thắc mắc về quy chế đào tạo, học bổng và thủ tục học tập kèm trích dẫn số trang, điều khoản từ văn bản gốc.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href={ROUTES.ADMIN.DOCUMENTS}>
            <Card className="h-full cursor-pointer border-border shadow-xs transition-all hover:border-brand-primary/50 hover:bg-brand-primary/5">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary">
                  <FileText className="h-5 w-5" />
                </div>
                <CardTitle className="text-base font-bold text-heading">
                  Kho Quy chế & Biểu mẫu
                </CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  Lưu trữ và tra cứu toàn bộ quyết định, quy định đào tạo, hướng dẫn làm đồ án tốt nghiệp và biểu mẫu chính thức.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link href={ROUTES.ADMIN.DASHBOARD}>
            <Card className="h-full cursor-pointer border-border shadow-xs transition-all hover:border-brand-primary/50 hover:bg-brand-primary/5">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <CardTitle className="text-base font-bold text-heading">
                  Quản trị & Đồng bộ
                </CardTitle>
                <CardDescription className="text-xs leading-relaxed">
                  Hệ thống tự động theo dõi, thu thập văn bản mới từ cổng đào tạo và quản lý quyền truy cập dữ liệu an toàn.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>
      </div>

      {/* Clean Footer (without internal joke/placeholder text) */}
      <footer className="border-t border-border bg-surface py-6 text-center text-xs text-muted">
        <p>© {new Date().getFullYear()} Trường Đại học Xây dựng Hà Nội (HUCE)</p>
      </footer>
    </main>
  )
}
