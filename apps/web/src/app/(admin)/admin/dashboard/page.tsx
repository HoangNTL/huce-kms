import * as React from "react"
import { Metadata } from "next"
import { FileText, Users, Database, Globe, CheckCircle2, ArrowUpRight } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export const metadata: Metadata = {
  title: "Bảng điều khiển Tổng quan | HUCE KMS Admin",
  description: "Thống kê tri thức, trạng thái RAG và hệ thống AI",
}

const metrics = [
  {
    title: "Tổng số tài liệu",
    value: "248",
    change: "+12 tuần này",
    icon: FileText,
    accent: "text-brand-primary bg-brand-primary-subtle",
  },
  {
    title: "Chunks đã Index Vector",
    value: "14,520",
    change: "98.2% tỷ lệ hoàn tất",
    icon: Database,
    accent: "text-success bg-success/10",
  },
  {
    title: "Người dùng hoạt động",
    value: "1,850",
    change: "+140 sinh viên mới",
    icon: Users,
    accent: "text-brand-primary-accent bg-brand-primary-accent/10",
  },
  {
    title: "Nguồn Crawl tự động",
    value: "8 nguồn",
    change: "Tất cả đang hoạt động",
    icon: Globe,
    accent: "text-warning bg-warning/10",
  },
]

export default function AdminDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="font-heading text-xl font-bold text-heading">Tổng quan Hệ thống</h2>
        <p className="text-xs text-muted">
          Theo dõi số liệu tài liệu tri thức, trạng thái vector chunks và sức khỏe dịch vụ AI
        </p>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((item, idx) => {
          const Icon = item.icon
          return (
            <Card key={idx} className="border-border shadow-xs">
              <CardContent className="flex items-center justify-between p-5">
                <div className="space-y-1">
                  <p className="text-xs font-medium text-muted">{item.title}</p>
                  <p className="font-heading text-2xl font-bold text-heading">{item.value}</p>
                  <p className="flex items-center gap-1 text-[11px] font-medium text-muted">
                    <ArrowUpRight className="h-3 w-3 text-success" />
                    <span>{item.change}</span>
                  </p>
                </div>
                <div
                  className={`flex h-11 w-11 items-center justify-center rounded-xl ${item.accent}`}
                >
                  <Icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* System Health */}
        <Card className="border-border shadow-xs">
          <CardHeader>
            <CardTitle className="font-heading text-sm font-bold text-heading">
              Sức khỏe Dịch vụ Nền tảng
            </CardTitle>
            <CardDescription className="text-xs">
              Trạng thái kết nối của FastAPI Backend, Postgres & Qdrant Vector DB
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" />
                <span className="font-medium text-heading">FastAPI Backend API</span>
              </div>
              <Badge
                variant="outline"
                className="border-success/30 bg-success/10 text-[11px] text-success"
              >
                Hoạt động bình thường
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" />
                <span className="font-medium text-heading">PostgreSQL Database</span>
              </div>
              <Badge
                variant="outline"
                className="border-success/30 bg-success/10 text-[11px] text-success"
              >
                Đã kết nối
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-success" />
                <span className="font-medium text-heading">Vector Database (Qdrant)</span>
              </div>
              <Badge
                variant="outline"
                className="border-success/30 bg-success/10 text-[11px] text-success"
              >
                Đã kết nối
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Recent Document Processing */}
        <Card className="border-border shadow-xs">
          <CardHeader>
            <CardTitle className="font-heading text-sm font-bold text-heading">
              Tài liệu Mới Nạp gần đây
            </CardTitle>
            <CardDescription className="text-xs">
              Tiến trình trích xuất và bóc tách chunks mới nhất
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div>
                <p className="font-medium text-heading">Quy chế đào tạo chính quy 2024</p>
                <p className="text-[11px] text-muted">148 chunks • Tải lên 2 giờ trước</p>
              </div>
              <Badge
                variant="default"
                className="border-success/30 bg-success/15 text-[10px] text-success"
              >
                INDEXED
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div>
                <p className="font-medium text-heading">Hướng dẫn thực hiện đồ án tốt nghiệp</p>
                <p className="text-[11px] text-muted">92 chunks • Tải lên 5 giờ trước</p>
              </div>
              <Badge
                variant="default"
                className="border-success/30 bg-success/15 text-[10px] text-success"
              >
                INDEXED
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5">
              <div>
                <p className="font-medium text-heading">Quyết định mức thu học phí năm 2024-2025</p>
                <p className="text-[11px] text-muted">Đang phân tích văn bản...</p>
              </div>
              <Badge
                variant="secondary"
                className="animate-pulse border-warning/30 bg-warning/15 text-[10px] text-warning"
              >
                PROCESSING
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
