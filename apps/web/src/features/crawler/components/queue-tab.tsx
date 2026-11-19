"use client"

import * as React from "react"
import { ExternalLink, Trash2 } from "lucide-react"
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
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { toast } from "@/components/ui/sonner"
import { crawlerService, type QueueResponse } from "@/features/crawler"
import type { CategoryItem } from "@/features/categories"

interface QueueTabProps {
  categories: CategoryItem[]
  onCompleted?: () => void
}

function formatQueueUrl(urlStr: string): { domain: string; path: string } {
  try {
    const u = new URL(urlStr)
    return { domain: u.hostname, path: decodeURIComponent(u.pathname + u.search) }
  } catch {
    return { domain: "", path: urlStr }
  }
}

export function QueueTab({ categories, onCompleted }: QueueTabProps) {
  const [queueData, setQueueData] = React.useState<QueueResponse | null>(null)
  const [isStartingQueue, setIsStartingQueue] = React.useState(false)
  const [isClearingQueue, setIsClearingQueue] = React.useState(false)
  const [removingUrl, setRemovingUrl] = React.useState<string | null>(null)
  const [queueCategoryId, setQueueCategoryId] = React.useState<string>("NONE")
  const [queuePage, setQueuePage] = React.useState(1)
  const [queuePageSize, setQueuePageSize] = React.useState(10)

  const loadQueue = React.useCallback(async () => {
    try {
      const data = await crawlerService.getQueue()
      setQueueData(data)
    } catch {
      toast.error("Không thể nạp dữ liệu hàng đợi")
    }
  }, [])

  React.useEffect(() => {
    let ignore = false
    crawlerService
      .getQueue()
      .then((data) => {
        if (!ignore) setQueueData(data)
      })
      .catch(() => {
        if (!ignore) toast.error("Không thể nạp dữ liệu hàng đợi")
      })
    return () => {
      ignore = true
    }
  }, [])

  const approvedUrls = React.useMemo(() => queueData?.approved_urls || [], [queueData])

  const paginatedQueueUrls = React.useMemo(() => {
    const start = (queuePage - 1) * queuePageSize
    return approvedUrls.slice(start, start + queuePageSize)
  }, [approvedUrls, queuePage, queuePageSize])

  const handleStartQueue = async () => {
    if (approvedUrls.length === 0) return
    setIsStartingQueue(true)
    try {
      const res = await crawlerService.startQueue({
        auto_ingest: true,
        auto_publish: false,
        category_id: queueCategoryId !== "NONE" ? queueCategoryId : undefined,
        clear_queue: true,
      })
      toast.success(`Thu thập hoàn tất ${res.successful}/${res.total} liên kết`, {
        description: `Mã phiên: ${res.session_id}`,
      })
      await loadQueue()
      onCompleted?.()
    } catch (err) {
      toast.error("Thu thập hàng đợi thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
      })
    } finally {
      setIsStartingQueue(false)
    }
  }

  const handleClearQueue = async () => {
    setIsClearingQueue(true)
    try {
      await crawlerService.clearQueue()
      await loadQueue()
      setQueuePage(1)
      toast.success("Đã làm trống hàng đợi")
    } catch {
      toast.error("Không thể xóa hàng đợi")
    } finally {
      setIsClearingQueue(false)
    }
  }

  const handleRemoveQueueItem = async (url: string) => {
    if (removingUrl) return
    setRemovingUrl(url)
    try {
      await crawlerService.removeQueueItem(url)
      await loadQueue()
      if (paginatedQueueUrls.length === 1 && queuePage > 1) {
        setQueuePage((p) => p - 1)
      }
      toast.success("Đã xóa liên kết khỏi hàng đợi")
    } catch {
      toast.error("Xóa liên kết thất bại")
    } finally {
      setRemovingUrl(null)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="border-border shadow-xs py-0 gap-0 overflow-hidden">
        {/* Header Bar with Action Controls */}
        <div className="flex flex-col gap-3 p-4 border-b border-border/60 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-heading">Hàng đợi</span>
            {approvedUrls.length > 0 && (
              <span className="text-xs text-muted font-normal">
                ({approvedUrls.length} liên kết)
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {approvedUrls.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted whitespace-nowrap">Lưu vào danh mục:</span>
                <div className="w-48">
                  <Select
                    value={queueCategoryId}
                    onValueChange={(val) => setQueueCategoryId(val ?? "NONE")}
                  >
                    <SelectTrigger className="h-8 rounded-lg text-xs font-normal">
                      <SelectValue placeholder="Chưa phân loại">
                        {(val) => {
                          if (!val || val === "NONE") return "Chưa phân loại"
                          const found = categories.find((c) => String(c.id) === String(val))
                          return found ? found.name : "Chưa phân loại"
                        }}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent align="start" className="min-w-56">
                      <SelectItem value="NONE">Chưa phân loại</SelectItem>
                      {categories.map((cat) => (
                        <SelectItem key={String(cat.id)} value={String(cat.id)}>
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {approvedUrls.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearQueue}
                disabled={isClearingQueue || isStartingQueue}
                className="h-8 px-3 text-xs text-slate-600 hover:text-rose-600 hover:bg-rose-50 hover:border-rose-200 border-border/80 rounded-lg gap-1.5"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Xóa hàng đợi</span>
              </Button>
            )}

            <Button
              size="sm"
              onClick={handleStartQueue}
              disabled={approvedUrls.length === 0 || isStartingQueue}
              loading={isStartingQueue}
              loadingText="Đang thu thập..."
              className="h-8 px-3.5 text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary-hover shadow-xs rounded-lg"
            >
              {approvedUrls.length > 0
                ? `Thu thập tất cả (${approvedUrls.length})`
                : "Thu thập tất cả"}
            </Button>
          </div>
        </div>

        {/* Content: Standard Table with TableHeader */}
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                  <TableHead className="text-2xs font-semibold uppercase tracking-wider text-slate-400 pl-4">
                    Địa chỉ liên kết
                  </TableHead>
                  <TableHead className="w-20 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400 pr-4">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {approvedUrls.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={2} className="h-32 text-center text-xs text-muted">
                      Hàng đợi hiện đang trống. Hãy qua tab &quot;Khám phá&quot; để tìm và duyệt liên kết.
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedQueueUrls.map((url, i) => {
                    const { domain, path } = formatQueueUrl(url)
                    return (
                      <TableRow key={url || i} className="transition-colors hover:bg-slate-50/60">
                        <TableCell className="py-2.5 pl-4 font-mono text-xs">
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 hover:text-brand-primary truncate max-w-3xl transition-colors group"
                            title={url}
                          >
                            {domain ? (
                              <>
                                <span className="text-slate-500 font-semibold shrink-0">{domain}</span>
                                <span className="text-muted truncate">{path}</span>
                              </>
                            ) : (
                              <span className="text-heading truncate">{url}</span>
                            )}
                            <ExternalLink className="h-3 w-3 shrink-0 text-muted opacity-60 group-hover:opacity-100" />
                          </a>
                        </TableCell>
                        <TableCell className="w-20 text-center pr-4">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => handleRemoveQueueItem(url)}
                            disabled={Boolean(removingUrl) || isStartingQueue}
                            loading={removingUrl === url}
                            className="h-7 w-7 rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors mx-auto"
                            title="Xóa liên kết này khỏi hàng đợi"
                            aria-label="Xóa liên kết khỏi hàng đợi"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>

          {approvedUrls.length > queuePageSize && (
            <DataTablePagination
              currentPage={queuePage}
              pageSize={queuePageSize}
              totalItems={approvedUrls.length}
              onPageChange={setQueuePage}
              onPageSizeChange={(newSize) => {
                setQueuePageSize(newSize)
                setQueuePage(1)
              }}
              pageSizeOptions={[10, 20, 50]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
