"use client"

import * as React from "react"
import Link from "next/link"
import { Eye, Database } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
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

export function SessionsTab() {
  const [sessions, setSessions] = React.useState<Array<Record<string, unknown>>>([])
  const [ingestingSessionId, setIngestingSessionId] = React.useState<string | null>(null)
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

  const paginatedSessions = React.useMemo(() => {
    const start = (sessionPage - 1) * sessionPageSize
    return sessions.slice(start, start + sessionPageSize)
  }, [sessions, sessionPage, sessionPageSize])

  const handleIngestSession = async (sessionId: string) => {
    if (ingestingSessionId) return
    setIngestingSessionId(sessionId)
    try {
      await crawlerService.ingest({ session_id: sessionId, auto_publish: true })
      toast.success(`Đã nạp toàn bộ phiên vào kho tài liệu`)
      await loadSessions()
    } catch (err) {
      toast.error("Nạp vào kho tài liệu thất bại", {
        description: err instanceof Error ? err.message : "Lỗi xử lý tài liệu.",
      })
    } finally {
      setIngestingSessionId(null)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="border-border shadow-xs py-0 gap-0 overflow-hidden">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-heading">Nhật ký phiên thu thập</span>
            {sessions.length > 0 && (
              <span className="text-xs text-muted font-normal">
                ({sessions.length} phiên)
              </span>
            )}
          </div>
        </div>

        {/* Content: Standard Table */}
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                  <TableHead className="w-auto text-2xs font-semibold uppercase tracking-wider text-slate-400 pl-4">
                    Phiên thu thập
                  </TableHead>
                  <TableHead className="w-36 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Kết quả
                  </TableHead>
                  <TableHead className="w-28 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400 pr-4">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="h-32 text-center text-xs text-muted">
                      Chưa có phiên thu thập nào được ghi nhận.
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedSessions.map((s, idx) => {
                    const sid = String(s.session_id || s.id || `session-${idx}`)
                    const total = Number(s.total_urls ?? s.total ?? 0)
                    const succ = Number(s.successful ?? s.succeeded ?? s.success_count ?? 0)
                    const started = String(s.started_at || s.created_at || "—")
                    const isIngesting = ingestingSessionId === sid

                    const resultColor =
                      succ === total && total > 0
                        ? "text-emerald-700 bg-emerald-50 border-emerald-200"
                        : succ > 0
                        ? "text-amber-700 bg-amber-50 border-amber-200"
                        : "text-rose-700 bg-rose-50 border-rose-200"

                    return (
                      <TableRow key={idx} className="transition-colors hover:bg-slate-50/60">
                        <TableCell className="w-auto py-2.5 pl-4">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-semibold text-heading">
                              {formatDateTime(started)}
                            </span>
                            <span className="font-mono text-2xs text-muted truncate max-w-md" title={sid}>
                              {sid}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="w-36 text-center py-2.5">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-2xs font-semibold border ${resultColor}`}
                          >
                            {succ}/{total} bài
                          </span>
                        </TableCell>
                        <TableCell className="w-28 text-center py-2.5 pr-4">
                          <div className="flex items-center justify-center gap-1.5">
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
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => handleIngestSession(sid)}
                              disabled={Boolean(ingestingSessionId)}
                              loading={isIngesting}
                              className="h-7 w-7 rounded-lg text-brand-primary hover:bg-brand-primary/10 hover:text-brand-primary"
                              title="Lưu toàn bộ phiên vào kho tài liệu"
                              aria-label="Lưu toàn bộ phiên vào kho tài liệu"
                            >
                              <Database className="h-3.5 w-3.5" />
                            </Button>
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
