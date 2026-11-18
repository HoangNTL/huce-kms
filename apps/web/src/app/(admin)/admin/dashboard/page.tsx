"use client"

import * as React from "react"
import Link from "next/link"
import {
  FileText,
  Users,
  Database,
  HardDrive,
  ArrowUpRight,
  RefreshCw,
  Plus,
  ArrowRight,
  Server,
  Layers,
  Cpu,
  FolderOpen,
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { dashboardService, type DashboardStats, type ServiceStatus } from "@/features/dashboard"
import {
  documentService,
  type DocumentMetadata,
  DocumentStatusBadge,
  DocumentUploadModal,
} from "@/features/documents"
import { ROUTES } from "@/constants/routes"

function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 MB"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function getServiceIcon(name: string) {
  const lower = name.toLowerCase()
  if (lower.includes("postgres") || lower.includes("database")) {
    return { icon: Database, bg: "bg-blue-50 text-blue-600 border-blue-100", role: "Cơ sở dữ liệu quan hệ" }
  }
  if (lower.includes("qdrant") || lower.includes("vector")) {
    return { icon: Layers, bg: "bg-emerald-50 text-emerald-600 border-emerald-100", role: "Cơ sở dữ liệu vector RAG" }
  }
  if (lower.includes("fastapi") || lower.includes("backend")) {
    return { icon: Server, bg: "bg-indigo-50 text-indigo-600 border-indigo-100", role: "Cổng giao tiếp API hệ thống" }
  }
  if (lower.includes("gemini") || lower.includes("ai")) {
    return { icon: Cpu, bg: "bg-amber-50 text-amber-600 border-amber-100", role: "Mô hình ngôn ngữ và vector nhúng" }
  }
  return { icon: Server, bg: "bg-slate-50 text-slate-600 border-slate-100", role: "Dịch vụ hệ thống" }
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      {/* Header Bar Skeleton */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-8 w-24 rounded-lg" />
      </div>

      {/* Metric Cards Grid Skeleton */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, idx) => (
          <Card key={idx} className="rounded-2xl border border-border bg-surface p-4 py-3.5 shadow-xs">
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <Skeleton className="h-10 w-10 rounded-xl" />
                <Skeleton className="h-5 w-20 rounded-full" />
              </div>
              <div className="space-y-1">
                <Skeleton className="h-7 w-24" />
                <Skeleton className="h-3.5 w-32" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Two Column Section Skeleton */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="rounded-2xl border border-border bg-surface p-5 shadow-xs space-y-3">
          <Skeleton className="h-5 w-44" />
          <div className="space-y-2.5">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="flex items-center justify-between rounded-xl border border-border/80 p-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="space-y-1.5">
                    <Skeleton className="h-4 w-28" />
                    <Skeleton className="h-3 w-36" />
                  </div>
                </div>
                <Skeleton className="h-6 w-16 rounded-md" />
              </div>
            ))}
          </div>
        </Card>

        <Card className="rounded-2xl border border-border bg-surface p-5 shadow-xs space-y-3">
          <Skeleton className="h-5 w-44" />
          <div className="space-y-2.5">
            {Array.from({ length: 3 }).map((_, idx) => (
              <div key={idx} className="flex items-center justify-between rounded-xl border border-border/80 p-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-9 w-9 rounded-lg" />
                  <div className="space-y-1.5">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
                <Skeleton className="h-6 w-20 rounded-full" />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default function AdminDashboardPage() {
  const [stats, setStats] = React.useState<DashboardStats | null>(null)
  const [recentDocs, setRecentDocs] = React.useState<DocumentMetadata[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [isRefreshing, setIsRefreshing] = React.useState(false)
  const [isUploadOpen, setIsUploadOpen] = React.useState(false)

  const [refreshKey, setRefreshKey] = React.useState(0)

  React.useEffect(() => {
    let ignore = false
    Promise.allSettled([
      dashboardService.getStats(),
      documentService.getDocuments({ page: 1, pageSize: 4 }),
    ]).then(([statsRes, docsRes]) => {
      if (ignore) return
      if (statsRes.status === "fulfilled") {
        setStats(statsRes.value)
      }
      if (docsRes.status === "fulfilled") {
        setRecentDocs(docsRes.value.items || [])
      }
      setIsLoading(false)
      setIsRefreshing(false)
    })

    return () => {
      ignore = true
    }
  }, [refreshKey])

  const handleRefresh = React.useCallback(() => {
    setIsRefreshing(true)
    setRefreshKey((prev) => prev + 1)
  }, [])

  if (isLoading) {
    return <DashboardSkeleton />
  }

  const metrics = [
    {
      title: "Tổng số tài liệu",
      value: stats ? stats.total_documents.toLocaleString() : "0",
      subBadge: stats ? `${stats.total_categories} danh mục` : "Khởi tạo",
      icon: FileText,
      squircle: "bg-indigo-50 text-indigo-600 border-indigo-100",
      badgeStyle: "bg-indigo-50 text-indigo-700 border-indigo-200/60",
    },
    {
      title: "Chunks đã Index Vector",
      value: stats ? stats.total_chunks.toLocaleString() : "0",
      subBadge: "Qdrant Ready",
      icon: Layers,
      squircle: "bg-emerald-50 text-emerald-600 border-emerald-100",
      badgeStyle: "bg-emerald-50 text-emerald-700 border-emerald-200/60",
    },
    {
      title: "Người dùng hệ thống",
      value: stats ? stats.total_users.toLocaleString() : "0",
      subBadge: stats ? `${stats.active_users} kích hoạt` : "0 hoạt động",
      icon: Users,
      squircle: "bg-sky-50 text-sky-600 border-sky-100",
      badgeStyle: "bg-sky-50 text-sky-700 border-sky-200/60",
    },
    {
      title: "Dung lượng Kho tri thức",
      value: formatBytes(stats?.total_file_size_bytes),
      subBadge: stats ? `${stats.indexed_documents ?? stats.total_documents} đã lập chỉ mục` : "Sẵn sàng",
      icon: HardDrive,
      squircle: "bg-amber-50 text-amber-600 border-amber-100",
      badgeStyle: "bg-amber-50 text-amber-700 border-amber-200/60",
    },
  ]

  return (
    <div className="space-y-4">
      {/* Header Bar: Clean & Focused */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
            Tổng quan Hệ thống
          </h1>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="h-8 gap-1.5 border-border bg-surface text-xs font-medium text-heading hover:bg-surface-hover"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>Làm mới</span>
        </Button>
      </div>

      {/* Metric Cards Grid (Modern Squircle + Pill Badge Pattern) */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((item, idx) => {
          const Icon = item.icon
          return (
            <Card
              key={idx}
              className="group relative overflow-hidden rounded-2xl border border-border bg-surface p-4 py-3.5 gap-0 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="space-y-2.5">
                {/* Top Row: Icon squircle on left, Pill badge on right */}
                <div className="flex items-center justify-between">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl border ${item.squircle} shadow-2xs transition-transform duration-200 group-hover:scale-105`}
                  >
                    <Icon className="h-4.5 w-4.5" />
                  </div>
                  <span
                    className={`flex items-center gap-1 rounded-full border px-2 py-0.5 text-2xs font-semibold tracking-tight ${item.badgeStyle}`}
                  >
                    <ArrowUpRight className="h-3 w-3" />
                    {item.subBadge}
                  </span>
                </div>

                {/* Main Metric Value */}
                <div className="space-y-0.5">
                  <p className="font-heading text-2xl font-extrabold tracking-tight text-heading">
                    {item.value}
                  </p>
                  <p className="text-xs font-semibold text-heading/85">{item.title}</p>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Two Column Section */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* System Health */}
        <Card className="rounded-2xl border border-border bg-surface shadow-xs py-0 gap-0">
          <CardHeader className="px-5 pt-4 pb-3">
            <CardTitle className="font-heading text-sm font-bold text-heading">
              Sức khỏe Dịch vụ Nền tảng
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 px-5 pb-4 text-xs">
            {stats?.services && stats.services.length > 0 ? (
              stats.services.map((svc: ServiceStatus, idx: number) => {
                const isHealthy = svc.status === "healthy"
                const meta = getServiceIcon(svc.name)
                const ServiceIcon = meta.icon
                const latency =
                  svc.latency_ms != null && typeof svc.latency_ms === "number"
                    ? `${svc.latency_ms} ms`
                    : null

                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between rounded-xl border border-border/80 bg-surface/50 p-3 transition-colors hover:bg-surface-hover/70"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${meta.bg}`}
                      >
                        <ServiceIcon className="h-4.5 w-4.5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-heading">{svc.name}</span>
                          <span className="relative flex h-2 w-2">
                            {isHealthy && (
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                            )}
                            <span
                              className={`relative inline-flex h-2 w-2 rounded-full ${
                                isHealthy ? "bg-emerald-500" : "bg-warning"
                              }`}
                            ></span>
                          </span>
                        </div>
                        <p className="text-2xs text-muted">
                          {svc.details || meta.role}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {latency && (
                        <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-2xs font-mono text-slate-600">
                          {latency}
                        </span>
                      )}
                      <Badge
                        variant="outline"
                        className={
                          isHealthy
                            ? "border-emerald-200/80 bg-emerald-50/80 text-2xs font-medium text-emerald-700"
                            : "border-warning/30 bg-warning/10 text-2xs font-medium text-warning"
                        }
                      >
                        {isHealthy ? "Sẵn sàng" : "Cần kiểm tra"}
                      </Badge>
                    </div>
                  </div>
                )
              })
            ) : (
              <p className="py-4 text-center text-xs text-muted">
                Chưa nhận được phản hồi từ dịch vụ theo dõi.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Recent Document Processing */}
        <Card className="rounded-2xl border border-border bg-surface shadow-xs py-0 gap-0">
          <CardHeader className="flex flex-row items-center justify-between px-5 pt-4 pb-3">
            <div>
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Tài liệu Tri thức Mới nhất
              </CardTitle>
              <CardDescription className="text-xs text-muted">
                Các văn bản, quyết định và quy chế vừa nạp vào cơ sở dữ liệu
              </CardDescription>
            </div>
            <Link
              href={ROUTES.ADMIN.DOCUMENTS}
              className="flex items-center gap-1 text-xs font-semibold text-brand-primary hover:underline"
            >
              <span>Xem tất cả</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-2.5 px-5 pb-4 text-xs">
            {recentDocs.length > 0 ? (
              recentDocs.map((doc) => {
                const chunks = doc.chunk_count ?? 0
                return (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between rounded-xl border border-border/80 bg-surface/50 p-3 transition-colors hover:bg-surface-hover/70"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50 text-indigo-600">
                        <FileText className="h-4.5 w-4.5" />
                      </div>
                      <div className="overflow-hidden">
                        <Link
                          href={ROUTES.ADMIN.DOCUMENT_DETAIL(String(doc.id))}
                          className="truncate font-semibold text-heading hover:text-brand-primary transition-colors block"
                          title={doc.title}
                        >
                          {doc.title}
                        </Link>
                        <p className="text-2xs text-muted">
                          {chunks} chunks • {formatBytes(doc.file_size)} •{" "}
                          <span className="text-slate-700 font-medium">
                            {typeof doc.category === "object" && doc.category !== null
                              ? doc.category.name
                              : (doc.category || "Quy chế chung")}
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="shrink-0 pl-2">
                      <DocumentStatusBadge status={doc.status} />
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-8 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                  <FolderOpen className="h-5 w-5" />
                </div>
                <h4 className="mt-2 text-xs font-semibold text-heading">
                  Chưa có tài liệu
                </h4>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsUploadOpen(true)}
                  className="mt-3 h-8 gap-1.5 border-brand-primary/30 text-xs font-medium text-brand-primary hover:bg-brand-primary-subtle"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>Tải lên</span>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Document Upload Modal */}
      <DocumentUploadModal
        open={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onSuccess={() => setRefreshKey((prev) => prev + 1)}
      />
    </div>
  )
}
