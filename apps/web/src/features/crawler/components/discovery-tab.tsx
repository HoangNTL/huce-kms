"use client"

import * as React from "react"
import { ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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
import { cn } from "@/lib/utils"
import { crawlerService, type DiscoverResult } from "@/features/crawler"

interface DiscoveryTabProps {
  onApproved?: () => void
}

export function DiscoveryTab({ onApproved }: DiscoveryTabProps) {
  const [discoveryUrl, setDiscoveryUrl] = React.useState("")
  const [maxItems, setMaxItems] = React.useState(30)
  const [isDiscovering, setIsDiscovering] = React.useState(false)
  const [isApproving, setIsApproving] = React.useState(false)
  const [discoveryResult, setDiscoveryResult] = React.useState<DiscoverResult | null>(null)
  const [selectedUrls, setSelectedUrls] = React.useState<Set<string>>(new Set())
  const [discoveryPage, setDiscoveryPage] = React.useState(1)
  const [discoveryPageSize, setDiscoveryPageSize] = React.useState(10)

  const paginatedDiscoveredItems = React.useMemo(() => {
    if (!discoveryResult?.items) return []
    const start = (discoveryPage - 1) * discoveryPageSize
    return discoveryResult.items.slice(start, start + discoveryPageSize)
  }, [discoveryResult, discoveryPage, discoveryPageSize])

  const handleDiscovery = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault()
    const trimmed = discoveryUrl.trim()
    if (!trimmed) {
      toast.error("Vui lòng nhập URL trang danh mục / sitemap")
      return
    }

    const parsedMax = Number(maxItems) || 30
    if (parsedMax < 1 || parsedMax > 200) {
      toast.error("Số lượng khám phá phải từ 1 đến 200 bài viết")
      return
    }

    setIsDiscovering(true)
    setDiscoveryResult(null)
    setSelectedUrls(new Set())
    setDiscoveryPage(1)
    try {
      const res = await crawlerService.discover({
        url: trimmed,
        max_items: parsedMax,
      })
      setDiscoveryResult(res)
      setSelectedUrls(new Set(res.items.map((i) => i.url)))
      toast.success(`Khám phá thành công ${res.total_discovered} liên kết bài viết`)
    } catch (err) {
      toast.error("Khám phá liên kết thất bại", {
        description: err instanceof Error ? err.message : "Lỗi đọc trang danh mục.",
      })
    } finally {
      setIsDiscovering(false)
    }
  }

  const toggleSelectUrl = (url: string) => {
    setSelectedUrls((prev) => {
      const next = new Set(prev)
      if (next.has(url)) next.delete(url)
      else next.add(url)
      return next
    })
  }

  const handleApproveSelected = async () => {
    if (!discoveryResult || selectedUrls.size === 0) {
      toast.error("Vui lòng chọn ít nhất một liên kết để duyệt")
      return
    }

    setIsApproving(true)
    try {
      const res = await crawlerService.approveQueue({
        queue_file: discoveryResult.queue_file,
        approved_urls: Array.from(selectedUrls),
      })
      toast.success(`Đã thêm ${res.total_approved} liên kết vào hàng đợi`)
      onApproved?.()
    } catch (err) {
      toast.error("Duyệt liên kết thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
      })
    } finally {
      setIsApproving(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="border-border shadow-xs py-0 gap-0">
        <CardContent className="p-4 sm:p-5">
          <form onSubmit={handleDiscovery} className="max-w-2xl flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <label className="text-xs font-medium text-heading">URL nguồn trang</label>
              <Input
                placeholder="https://daotao.huce.edu.vn/thong-bao"
                value={discoveryUrl}
                onChange={(e) => setDiscoveryUrl(e.target.value)}
                className="font-mono text-xs"
                disabled={isDiscovering}
              />
            </div>
            <div className="w-28 space-y-1.5">
              <label className="text-xs font-medium text-heading">Số lượng</label>
              <Input
                type="number"
                min={1}
                max={200}
                placeholder="30"
                value={maxItems || ""}
                onChange={(e) => {
                  const val = e.target.value === "" ? 0 : Number(e.target.value)
                  setMaxItems(val)
                }}
                onBlur={() => {
                  if (!maxItems || maxItems < 1) {
                    setMaxItems(1)
                    toast.warning("Số lượng tối thiểu là 1")
                  } else if (maxItems > 200) {
                    setMaxItems(200)
                    toast.warning("Số lượng tối đa là 200")
                  }
                }}
                className="text-xs"
                disabled={isDiscovering}
              />
            </div>
            <Button
              type="submit"
              loading={isDiscovering}
              loadingText="Đang quét liên kết..."
            >
              Khám phá
            </Button>
          </form>
        </CardContent>
      </Card>

      {discoveryResult && (
        <Card className="border-border shadow-xs py-0 gap-0 overflow-hidden">
          <div className="flex flex-col gap-3 p-4 border-b border-border/60 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-heading">
                Liên kết tìm thấy
              </span>
              <Badge variant="outline" className="border-emerald-500/30 bg-emerald-50 text-emerald-700 text-2xs">
                {discoveryResult.total_discovered}
              </Badge>
            </div>
            <Button
              onClick={handleApproveSelected}
              disabled={selectedUrls.size === 0 || isApproving}
              loading={isApproving}
              loadingText="Đang duyệt..."
              className="bg-emerald-600 text-xs text-white hover:bg-emerald-700 h-8 px-3 rounded-lg font-medium"
            >
              Duyệt ({selectedUrls.size})
            </Button>
          </div>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                    <TableHead className="w-12 text-center">
                      <input
                        type="checkbox"
                        checked={
                          selectedUrls.size === discoveryResult.items.length &&
                          discoveryResult.items.length > 0
                        }
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedUrls(new Set(discoveryResult.items.map((i) => i.url)))
                          } else {
                            setSelectedUrls(new Set())
                          }
                        }}
                        className="rounded border-border text-brand-primary cursor-pointer"
                        title="Chọn tất cả"
                      />
                    </TableHead>
                    <TableHead className="w-14 text-center text-2xs font-semibold uppercase tracking-wider text-slate-400">
                      STT
                    </TableHead>
                    <TableHead className="w-1/2 text-2xs font-semibold uppercase tracking-wider text-slate-400">
                      Tiêu đề bài viết
                    </TableHead>
                    <TableHead className="w-1/2 text-2xs font-semibold uppercase tracking-wider text-slate-400">
                      Địa chỉ URL
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedDiscoveredItems.map((item, idx) => {
                    const stt = (discoveryPage - 1) * discoveryPageSize + idx + 1
                    const isSelected = selectedUrls.has(item.url)
                    return (
                      <TableRow
                        key={item.url || idx}
                        className={cn(
                          "transition-colors hover:bg-slate-50/60",
                          isSelected && "bg-brand-primary/5"
                        )}
                      >
                        <TableCell className="w-12 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectUrl(item.url)}
                            className="rounded border-border text-brand-primary cursor-pointer"
                          />
                        </TableCell>
                        <TableCell className="w-14 text-center text-xs font-medium text-slate-500">
                          {stt}
                        </TableCell>
                        <TableCell className="w-1/2 text-xs font-medium text-heading">
                          {item.title || "—"}
                        </TableCell>
                        <TableCell className="w-1/2 font-mono text-2xs text-muted">
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline hover:text-brand-primary break-all inline-flex items-center gap-1.5"
                            title={item.url}
                          >
                            <span>{item.url}</span>
                            <ExternalLink className="h-3 w-3 shrink-0 text-muted" />
                          </a>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>

            <DataTablePagination
              currentPage={discoveryPage}
              pageSize={discoveryPageSize}
              totalItems={discoveryResult.items.length}
              onPageChange={setDiscoveryPage}
              onPageSizeChange={(newSize) => {
                setDiscoveryPageSize(newSize)
                setDiscoveryPage(1)
              }}
              pageSizeOptions={[10, 20, 50]}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
