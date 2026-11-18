"use client"

import * as React from "react"
import { RotateCw } from "lucide-react"
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
    return `${time} • ${date}`
  } catch {
    return dateStr
  }
}

export function SessionsTab() {
  const [sessions, setSessions] = React.useState<Array<Record<string, unknown>>>([])
  const [isLoadingSessions, setIsLoadingSessions] = React.useState(false)
  const [ingestingSessionId, setIngestingSessionId] = React.useState<string | null>(null)
  const [sessionPage, setSessionPage] = React.useState(1)
  const [sessionPageSize, setSessionPageSize] = React.useState(10)

  const loadSessions = React.useCallback(async () => {
    setIsLoadingSessions(true)
    try {
      const data = await crawlerService.getSessions()
      setSessions(data || [])
    } catch {
      toast.error("Không thể nạp lịch sử phiên thu thập")
    } finally {
      setIsLoadingSessions(false)
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
      toast.success(`Đã nạp toàn bộ phiên "${sessionId}" vào kho tài liệu`)
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
        <div className="flex items-center justify-between p-4 border-b border-border/60">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-heading">Nhật ký phiên thu thập</span>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={loadSessions}
            disabled={isLoadingSessions}
            className="h-8 w-8 text-muted hover:text-heading"
            title="Làm mới lịch sử"
            aria-label="Làm mới lịch sử"
          >
            <RotateCw className={`h-3.5 w-3.5 ${isLoadingSessions ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Content: Standard Table with TableHeader always visible */}
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                  <TableHead className="w-auto text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Mã phiên
                  </TableHead>
                  <TableHead className="w-48 text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Thời gian
                  </TableHead>
                  <TableHead className="w-24 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Tổng URL
                  </TableHead>
                  <TableHead className="w-24 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Thành công
                  </TableHead>
                  <TableHead className="w-32 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-32 text-center text-xs text-muted">
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

                    return (
                      <TableRow key={idx} className="transition-colors hover:bg-slate-50/60">
                        <TableCell className="w-auto font-mono text-xs font-semibold text-heading truncate" title={sid}>
                          {sid}
                        </TableCell>
                        <TableCell className="w-48 text-xs text-muted">{formatDateTime(started)}</TableCell>
                        <TableCell className="w-24 text-center text-xs font-medium">{total}</TableCell>
                        <TableCell className="w-24 text-center text-xs text-emerald-600 font-semibold">
                          {succ}
                        </TableCell>
                        <TableCell className="w-32 text-center">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleIngestSession(sid)}
                            disabled={Boolean(ingestingSessionId)}
                            loading={isIngesting}
                            loadingText="Đang lưu..."
                            className="h-7 text-xs border-brand-primary/40 text-brand-primary hover:bg-brand-primary/10 mx-auto min-w-20"
                          >
                            Lưu vào kho
                          </Button>
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
