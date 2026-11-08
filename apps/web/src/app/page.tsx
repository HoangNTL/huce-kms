"use client"

import * as React from "react"
import Link from "next/link"
import { Sparkles, MessageSquare, ShieldCheck, ArrowRight, FileText, LogIn } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { ROUTES } from "@/constants/routes"

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col justify-between bg-background">
      {/* Navigation Bar */}
      <header className="sticky top-0 z-30 border-b border-border bg-surface/80 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-primary text-white shadow-xs">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="font-heading text-base leading-tight font-bold text-heading">
                HUCE KMS
              </p>
              <p className="text-[10px] leading-none text-muted">Trường Đại học Xây dựng Hà Nội</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href={ROUTES.AUTH.LOGIN}>
              <Button variant="outline" size="sm" className="gap-1.5 text-xs">
                <LogIn className="h-3.5 w-3.5" />
                <span>Đăng nhập</span>
              </Button>
            </Link>
            <Link href={ROUTES.USER.CHAT}>
              <Button
                size="sm"
                className="gap-1.5 bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Vào Chat AI</span>
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="mx-auto flex max-w-5xl flex-1 flex-col items-center justify-center space-y-6 px-4 py-16 text-center sm:px-6">
        <Badge
          variant="outline"
          className="border-brand-primary/30 bg-brand-primary/5 px-3 py-1 text-xs text-brand-primary"
        >
          Nền tảng Tra cứu Tri thức & Trợ lý AI thế hệ mới
        </Badge>

        <h1 className="max-w-3xl font-heading text-3xl leading-tight font-extrabold tracking-tight text-heading sm:text-5xl">
          Hệ thống Quản trị Tri thức & Hỏi đáp AI Thông minh{" "}
          <span className="text-brand-primary">HUCE</span>
        </h1>

        <p className="max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
          Tra cứu nhanh chóng mọi quy chế đào tạo, hướng dẫn làm đồ án tốt nghiệp, biểu mẫu học tập
          và văn bản học thuật chính thức với nguồn trích dẫn đối chứng minh bạch.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
          <Link href={ROUTES.USER.CHAT}>
            <Button
              size="lg"
              className="gap-2 bg-brand-primary text-white shadow-xs hover:bg-brand-primary-hover"
            >
              <Sparkles className="h-4 w-4" />
              <span>Bắt đầu Trò chuyện với AI</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href={ROUTES.ADMIN.DASHBOARD}>
            <Button size="lg" variant="outline" className="gap-2">
              <ShieldCheck className="h-4 w-4 text-brand-primary" />
              <span>Giao diện Quản trị (Admin)</span>
            </Button>
          </Link>
        </div>

        {/* Portals Showcase */}
        <div className="grid w-full grid-cols-1 gap-4 pt-12 text-left sm:grid-cols-3">
          <Link href={ROUTES.USER.CHAT}>
            <Card className="h-full cursor-pointer border-border shadow-xs transition-all hover:border-brand-primary/50 hover:bg-brand-primary/5">
              <CardHeader>
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-primary/10 text-brand-primary">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <CardTitle className="text-base font-bold text-heading">Hỏi đáp AI (RAG)</CardTitle>
                <CardDescription className="text-xs">
                  Truy vấn thông tin tự động, streaming câu trả lời thời gian thực kèm trích dẫn văn
                  bản đối chứng.
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
                  Kho Tri thức & Chunks
                </CardTitle>
                <CardDescription className="text-xs">
                  Quản lý tài liệu PDF, DOCX, bóc tách chunks tự động và nạp vào vector database
                  Qdrant.
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
                  Bảng Quản trị Trung tâm
                </CardTitle>
                <CardDescription className="text-xs">
                  Theo dõi số liệu, quản lý người dùng, phân quyền vai trò và giám sát các tác vụ
                  crawler dữ liệu.
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-border bg-surface py-6 text-center text-xs text-muted">
        <p>
          © {new Date().getFullYear()} Trường Đại học Xây dựng Hà Nội (HUCE). Nền tảng Frontend hoàn
          thiện bởi Senior Frontend Engineer.
        </p>
      </footer>
    </main>
  )
}
