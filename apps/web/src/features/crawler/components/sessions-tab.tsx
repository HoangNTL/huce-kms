"use client"

import * as React from "react"
import Link from "next/link"
import { Eye, StopCircle, History } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { Empty, EmptyHeader, EmptyTitle, EmptyMedia } from "@/components/ui/empty"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { toast } from "@/components/ui/sonner"
import { crawlerService } from "@/features/crawler"
import { ROUTES } from "@/constants/routes"

function formatDateTime(dateStr?: string | null): string {
  if (!dateStr || dateStr === "—") return "—"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    const time = d.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    })
    const date = d.toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
    return `${time} · ${date}`
  } catch {
    return dateStr
  }
}

function renderStatusBadge(statusStr?: string, completed?: number, total?: number) {
  const st = String(statusStr || "completed").toLowerCase()
  if (st === "in_progress" || st === "pending") {
    return (
      <Badge
        variant="outline"
        className="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 border-blue-200 font-medium"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
        <span>Đang chạy ({completed ?? 0}/{total ?? 0})</span>
      </Badge>
    )
  }
  if (st === "cancelled") {
    return (
      <Badge
        variant="outline"
        className="text-slate-600 bg-slate-100 border-slate-200 font-medium"
      >
        Đã hủy
      </Badge>
    )
  }
  if (st === "interrupted") {
    return (
      <Badge
        variant="outline"
        className="text-amber-700 bg-amber-50 border-amber-200 font-medium"
      >
        Bị gián đoạn
      </Badge>
    )
  }
  if (st === "failed") {
    return (
      <Badge
        variant="outline"
        className="text-rose-700 bg-rose-50 border-rose-200 font-medium"
      >
        Thất bại
      </Badge>
    )
  }
  return (
    <Badge
      variant="outline"
      className="text-emerald-700 bg-emerald-50 border-emerald-200 font-medium"
    >
      Hoàn thành
    </Badge>
  )
}

export function SessionsTab() {
  const [sessions, setSessions] = React.useState<Array<Record<string, unknown>>>([])
  const [cancellingSessionId, setCancellingSessionId] = React.useState<string | null>(null)
  const [sessionPage, setSessionPage] = React.useState(1)
  const [sessionPageSize, setSessionPageSize] = React.useState(10)

  const loadSessions = React.useCallback(async () => {
    try {
      const data = await crawlerService.getSessions()
      setSessions(data || [])
    } catch {
      toast.error("Không thể nạp lịch sử phiên thu thập")
    }
  }, [])

  React.useEffect(() => {
    let ignore = false
    crawlerService
      .getSessions()
      .then((data) => {
        if (!ignore) setSessions(data || [])
      })
      .catch(() => {
        if (!ignore) toast.error("Không thể nạp lịch sử phiên thu thập")
      })
    return () => {
      ignore = true
    }
  }, [])

  // Auto-refresh when any session is active
  const hasActiveSession = React.useMemo(() => {
    return sessions.some((s) => {
      const st = String(s.status || "").toLowerCase()
      return st === "in_progress" || st === "pending"
    })
  }, [sessions])

  React.useEffect(() => {
    if (!hasActiveSession) return
    const interval = setInterval(() => {
      loadSessions()
    }, 3000)
    return () => clearInterval(interval)
  }, [hasActiveSession, loadSessions])

  const paginatedSessions = React.useMemo(() => {
    const start = (sessionPage - 1) * sessionPageSize
    return sessions.slice(start, start + sessionPageSize)
  }, [sessions, sessionPage, sessionPageSize])

  const handleCancelSession = async (sessionId: string) => {
    if (cancellingSessionId) return
    setCancellingSessionId(sessionId)
    try {
      await crawlerService.cancelSession(sessionId)
      toast.info("Đã gửi tín hiệu hủy phiên thu thập.")
      await loadSessions()
    } catch (err) {
      toast.error("Hủy phiên thu thập thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại.",
      })
    } finally {
      setCancellingSessionId(null)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="border-border shadow-xs py-0 gap-0 overflow-hidden">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
          <span className="text-sm font-semibold text-heading">Nhật ký phiên thu thập</span>
        </div>

        {/* Content: Standard 5-column Table */}
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                  <TableHead className="w-auto min-w-[200px] text-2xs font-semibold uppercase tracking-wider text-slate-400 pl-4">
                    Mã phiên
                  </TableHead>
                  <TableHead className="w-48 text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Thời gian bắt đầu
                  </TableHead>
                  <TableHead className="w-36 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Trạng thái
                  </TableHead>
                  <TableHead className="w-32 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Kết quả
                  </TableHead>
                  <TableHead className="w-24 text-right text-2xs font-semibold uppercase tracking-wider text-slate-400 pr-4">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-10 text-center">
                      <Empty className="border-0 p-0">
                        <EmptyMedia variant="icon" className="h-10 w-10 rounded-full bg-slate-100 text-slate-400">
                          <History className="h-5 w-5" />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle className="text-sm font-medium text-slate-600">
                            Chưa có phiên thu thập nào
                          </EmptyTitle>
                        </EmptyHeader>
                      </Empty>
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedSessions.map((s, idx) => {
                    const sid = String(s.session_id || s.id || `session-${idx}`)
                    const total = Number(s.total_urls ?? s.total ?? 0)
                    const completed = Number(s.completed_urls ?? total)
                    const succ = Number(s.successful ?? s.succeeded ?? s.success_count ?? 0)
                    const status = String(s.status || "completed").toLowerCase()
                    const started = String(s.started_at || s.created_at || "—")
                    const isCancelling = cancellingSessionId === sid
                    const isRunning = status === "in_progress" || status === "pending"

                    return (
                      <TableRow key={idx} className="transition-colors hover:bg-slate-50/60">
                        {/* Column 1: Mã phiên */}
                        <TableCell className="w-auto min-w-[200px] py-2.5 pl-4">
                          <Link
                            href={ROUTES.ADMIN.CRAWLER_SESSION(sid)}
                            className="font-mono text-xs font-semibold text-heading hover:text-brand-primary truncate max-w-sm block transition-colors"
                            title={`Xem chi tiết phiên: ${sid}`}
                          >
                            {sid}
                          </Link>
                        </TableCell>

                        {/* Column 2: Thời gian bắt đầu */}
                        <TableCell className="w-48 py-2.5 text-xs text-muted font-normal whitespace-nowrap">
                          {formatDateTime(started)}
                        </TableCell>

                        {/* Column 3: Trạng thái */}
                        <TableCell className="w-36 text-center py-2.5">
                          {renderStatusBadge(status, completed, total)}
                        </TableCell>

                        {/* Column 4: Kết quả */}
                        <TableCell className="w-32 text-center py-2.5">
                          <div className="text-xs font-medium text-heading tabular-nums">
                            <span>{succ}/{total} bài</span>
                            {total > succ && (
                              <span className="block text-2xs text-rose-500 font-normal">
                                ({total - succ} lỗi)
                              </span>
                            )}
                          </div>
                        </TableCell>

                        {/* Column 5: Thao tác */}
                        <TableCell className="w-24 text-right py-2.5 pr-4">
                          <div className="flex items-center justify-end gap-1.5">
                            {isRunning && (
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                onClick={() => handleCancelSession(sid)}
                                disabled={Boolean(cancellingSessionId)}
                                loading={isCancelling}
                                className="h-7 w-7 rounded-lg text-rose-600 hover:bg-rose-50 hover:text-rose-700"
                                title="Hủy phiên thu thập đang chạy"
                                aria-label="Hủy phiên thu thập đang chạy"
                              >
                                <StopCircle className="h-3.5 w-3.5" />
                              </Button>
                            )}
                            <Link href={ROUTES.ADMIN.CRAWLER_SESSION(sid)}>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="h-7 w-7 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                                title="Xem chi tiết phiên"
                                aria-label="Xem chi tiết phiên"
                              >
                                <Eye className="h-3.5 w-3.5" />
                              </Button>
                            </Link>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {sessions.length > sessionPageSize && (
            <DataTablePagination
              currentPage={sessionPage}
              pageSize={sessionPageSize}
              totalItems={sessions.length}
              onPageChange={setSessionPage}
              onPageSizeChange={(newSize) => {
                setSessionPageSize(newSize)
                setSessionPage(1)
              }}
              pageSizeOptions={[10, 20, 50]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
