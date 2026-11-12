"use client"

import * as React from "react"
import { FileText, Users, Database, Globe, CheckCircle2, AlertTriangle, ArrowUpRight, Loader2 } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { dashboardService, type DashboardStats } from "@/features/dashboard"
import { documentService, type DocumentMetadata } from "@/features/documents"

export default function AdminDashboardPage() {
  const [stats, setStats] = React.useState<DashboardStats | null>(null)
  const [recentDocs, setRecentDocs] = React.useState<DocumentMetadata[]>([])
  const [isLoading, setIsLoading] = React.useState(true)

  React.useEffect(() => {
    let ignore = false
    Promise.allSettled([
      dashboardService.getStats(),
      documentService.getDocuments({ page: 1, pageSize: 3 }),
    ]).then(([statsRes, docsRes]) => {
      if (ignore) return
      if (statsRes.status === "fulfilled") {
        setStats(statsRes.value)
      }
      if (docsRes.status === "fulfilled") {
        setRecentDocs(docsRes.value.items || [])
      }
      setIsLoading(false)
    })

    return () => {
      ignore = true
    }
  }, [])

  const metrics = [
    {
      title: "Tổng số tài liệu",
      value: stats ? stats.total_documents.toLocaleString() : "—",
      change: stats ? `${stats.total_categories} danh mục` : "Đang đồng bộ",
      icon: FileText,
      accent: "text-brand-primary bg-brand-primary-subtle",
    },
    {
      title: "Chunks đã Index Vector",
      value: stats ? stats.total_chunks.toLocaleString() : "—",
      change: "Qdrant Vector Engine",
      icon: Database,
      accent: "text-success bg-success/10",
    },
    {
      title: "Người dùng hệ thống",
      value: stats ? stats.total_users.toLocaleString() : "—",
      change: stats ? `${stats.active_users} tài khoản hoạt động` : "—",
      icon: Users,
      accent: "text-brand-primary-accent bg-brand-primary-accent/10",
    },
    {
      title: "Crawler Thu thập Tri thức",
      value: "Hybrid Mode",
      change: "Direct, Discovery, Queue",
      icon: Globe,
      accent: "text-warning bg-warning/10",
    },
  ]

  if (isLoading) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-xs text-muted">
        <Loader2 className="h-6 w-6 animate-spin text-brand-primary" />
        <span>Đang nạp dữ liệu thống kê tổng quan...</span>
      </div>
    )
  }

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
            {stats?.services && stats.services.length > 0 ? (
              stats.services.map((svc, idx) => {
                const isHealthy = svc.status === "healthy"
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5"
                  >
                    <div className="flex items-center gap-2">
                      {isHealthy ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-warning" />
                      )}
                      <div>
                        <span className="font-medium text-heading">{svc.name}</span>
                        {svc.details && (
                          <span className="ml-2 text-[10px] text-muted">({svc.details})</span>
                        )}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        isHealthy
                          ? "border-emerald-500/30 bg-emerald-50 text-[11px] text-emerald-700"
                          : "border-warning/30 bg-warning/10 text-[11px] text-warning"
                      }
                    >
                      {isHealthy ? "Hoạt động bình thường" : "Cần kiểm tra"}
                      {svc.latency_ms !== undefined && ` (${svc.latency_ms}ms)`}
                    </Badge>
                  </div>
                )
              })
            ) : (
              <p className="text-xs text-muted">Không có dữ liệu sức khỏe dịch vụ.</p>
            )}
          </CardContent>
        </Card>

        {/* Recent Document Processing */}
        <Card className="border-border shadow-xs">
          <CardHeader>
            <CardTitle className="font-heading text-sm font-bold text-heading">
              Tài liệu Tri thức Mới nhất
            </CardTitle>
            <CardDescription className="text-xs">
              Các văn bản, quy chế và phụ lục vừa nạp vào cơ sở dữ liệu
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {recentDocs.length > 0 ? (
              recentDocs.map((doc) => {
                const chunks = doc.chunk_count ?? 0
                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between rounded-lg border border-border bg-surface/50 p-2.5"
                  >
                    <div className="overflow-hidden">
                      <p className="truncate font-medium text-heading" title={doc.title}>
                        {doc.title}
                      </p>
                      <p className="text-[11px] text-muted">
                        {chunks} chunks • {doc.file_type || "pdf"}
                      </p>
                    </div>
                    <Badge
                      variant="default"
                      className="border-success/30 bg-success/15 text-[10px] text-success uppercase"
                    >
                      {doc.status || "INDEXED"}
                    </Badge>
                  </div>
                )
              })
            ) : (
              <p className="text-xs text-muted">Chưa có tài liệu nào trong hệ thống.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
