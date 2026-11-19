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

function parseTitleAndDate(rawTitle?: string | null): { cleanTitle: string; dateStr: string | null } {
  if (!rawTitle) return { cleanTitle: "—", dateStr: null }
  const trimmed = rawTitle.trim()
  const dateMatch = trimmed.match(/[-–—]?\s*(\d{1,2}[/.-]\d{1,2}[/.-]\d{4})\s*$/)
  if (dateMatch) {
    const clean = trimmed.slice(0, dateMatch.index).trim().replace(/[-–—]\s*$/, "")
    return {
      cleanTitle: clean || trimmed,
      dateStr: dateMatch[1],
    }
  }
  return { cleanTitle: trimmed, dateStr: null }
}

function getUrlDomainAndPath(urlStr: string): { domain: string; path: string } {
  try {
    const u = new URL(urlStr)
    return { domain: u.hostname, path: u.pathname }
  } catch {
    return { domain: "", path: urlStr }
  }
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
          <form onSubmit={handleDiscovery} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <label className="text-xs font-medium text-heading">URL nguồn trang</label>
              <Input
                placeholder="https://daotao.huce.edu.vn/thong-bao"
                value={discoveryUrl}
                onChange={(e) => setDiscoveryUrl(e.target.value)}
                className="font-mono text-xs h-9"
                disabled={isDiscovering}
              />
            </div>
            <div className="w-32 space-y-1.5 shrink-0">
              <label className="text-xs font-medium text-heading">Số bài tối đa</label>
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
                className="text-xs h-9"
                disabled={isDiscovering}
              />
            </div>
            <Button
              type="submit"
              loading={isDiscovering}
              loadingText="Đang quét liên kết..."
              className="h-9 px-4 text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary-hover shadow-xs shrink-0"
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
              <Badge variant="outline" className="border-border bg-slate-100 text-slate-700 text-2xs font-semibold">
                {discoveryResult.total_discovered} bài
              </Badge>
            </div>
            <Button
              onClick={handleApproveSelected}
              disabled={selectedUrls.size === 0 || isApproving}
              loading={isApproving}
              loadingText="Đang duyệt..."
              className="bg-brand-primary text-xs text-white hover:bg-brand-primary-hover h-8 px-3.5 rounded-lg font-semibold shadow-xs"
            >
              Duyệt ({selectedUrls.size})
            </Button>
          </div>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                    <TableHead className="w-10 text-center pl-4">
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
                    <TableHead className="w-auto text-2xs font-semibold uppercase tracking-wider text-slate-400">
                      Tiêu đề bài viết
                    </TableHead>
                    <TableHead className="w-28 text-right text-2xs font-semibold uppercase tracking-wider text-slate-400 pr-4">
                      Ngày
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedDiscoveredItems.map((item, idx) => {
                    const isSelected = selectedUrls.has(item.url)
                    const { cleanTitle, dateStr } = parseTitleAndDate(item.title)
                    const { domain, path } = getUrlDomainAndPath(item.url)

                    return (
                      <TableRow
                        key={item.url || idx}
                        className={cn(
                          "transition-colors hover:bg-slate-50/60",
                          isSelected && "bg-brand-primary/5"
                        )}
                      >
                        <TableCell className="w-10 text-center pl-4 py-2.5">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectUrl(item.url)}
                            className="rounded border-border text-brand-primary cursor-pointer"
                          />
                        </TableCell>
                        <TableCell className="w-auto py-2.5">
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-medium text-heading line-clamp-2">
                              {cleanTitle}
                            </span>
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 font-mono text-2xs text-muted hover:text-brand-primary truncate max-w-xl transition-colors"
                              title={item.url}
                            >
                              <span className="truncate">{domain ? `${domain}${path}` : item.url}</span>
                              <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
                            </a>
                          </div>
                        </TableCell>
                        <TableCell className="w-28 text-right font-mono text-2xs text-muted pr-4 whitespace-nowrap">
                          {dateStr || "—"}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>

            {discoveryResult.items.length > discoveryPageSize && (
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
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
