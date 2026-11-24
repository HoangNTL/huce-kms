"use client"

import * as React from "react"
import Link from "next/link"
import {
  ArrowUpRight,
  ExternalLink,
  HelpCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import { toast } from "@/components/ui/sonner"
import { crawlerService, type CrawlDirectResult } from "@/features/crawler"
import type { CategoryItem } from "@/features/categories"

interface DirectCrawlTabProps {
  categories: CategoryItem[]
}

export function DirectCrawlTab({ categories }: DirectCrawlTabProps) {
  const [directUrl, setDirectUrl] = React.useState("")
  const [selectedCategoryId, setSelectedCategoryId] = React.useState<string>("NONE")
  const [autoIngest, setAutoIngest] = React.useState(true)
  const [autoPublish, setAutoPublish] = React.useState(false)
  const [isCrawlingDirect, setIsCrawlingDirect] = React.useState(false)
  const [directResult, setDirectResult] = React.useState<CrawlDirectResult | null>(null)

  const handleDirectCrawl = async (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault()
    const trimmed = directUrl.trim()
    if (!trimmed) {
      toast.error("Vui lòng nhập địa chỉ URL bài viết cần thu thập")
      return
    }

    setIsCrawlingDirect(true)
    setDirectResult(null)
    try {
      const res = await crawlerService.crawlDirect({
        url: trimmed,
        auto_ingest: autoIngest,
        auto_publish: autoPublish,
        category_id: selectedCategoryId !== "NONE" ? selectedCategoryId : undefined,
      })
      // Snapshot the exact published/ingested status at the time of crawling
      setDirectResult({
        ...res,
        published: res.published ?? (autoPublish && res.ingested),
      })
      toast.success("Thu thập liên kết thành công")
    } catch (err) {
      toast.error("Thu thập thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng kiểm tra lại URL.",
      })
    } finally {
      setIsCrawlingDirect(false)
    }
  }

  return (
    <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0 overflow-hidden">
      <CardContent className="p-4 sm:p-5">
        <form onSubmit={handleDirectCrawl} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
            <div className="md:col-span-8 space-y-1.5">
              <label className="text-xs font-medium text-heading">URL bài viết</label>
              <Input
                placeholder="https://daotao.huce.edu.vn/thong-bao/..."
                value={directUrl}
                onChange={(e) => setDirectUrl(e.target.value)}
                className="font-mono text-xs h-9"
                disabled={isCrawlingDirect}
              />
            </div>
            <div className="md:col-span-4 space-y-1.5">
              <label className="text-xs font-medium text-heading">Danh mục tài liệu</label>
              <Select
                value={selectedCategoryId}
                onValueChange={(val) => setSelectedCategoryId(val ?? "NONE")}
              >
                <SelectTrigger className="h-9 w-full rounded-lg text-xs font-normal">
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

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-border/50">
            <div className="flex flex-wrap items-center gap-5 text-xs">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoIngest}
                  onChange={(e) => setAutoIngest(e.target.checked)}
                  className="rounded border-border text-brand-primary"
                />
                <span className="text-body font-medium">Lưu vào kho tài liệu</span>
              </label>
              {autoIngest && (
                <label className="flex items-center gap-2 cursor-pointer select-none" title="Chuyển đổi vector và nạp vào Qdrant để AI Assistant trả lời tra cứu">
                  <input
                    type="checkbox"
                    checked={autoPublish}
                    onChange={(e) => setAutoPublish(e.target.checked)}
                    className="rounded border-border text-brand-primary"
                  />
                  <span className="text-body font-medium">Lập chỉ mục tìm kiếm (RAG)</span>
                  <HelpCircle className="h-3.5 w-3.5 text-muted hover:text-heading cursor-help" />
                </label>
              )}
            </div>

            <Button
              type="submit"
              loading={isCrawlingDirect}
              loadingText="Đang thu thập..."
              className="h-9 px-4 text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary-hover shadow-xs self-start sm:self-auto"
            >
              Thu thập
            </Button>
          </div>
        </form>
      </CardContent>

      {/* Seamless integrated result panel - eliminates redundant gap and double borders */}
      {directResult && (
        <div className="border-t border-border/60 bg-slate-50/60 p-4 sm:p-5 transition-all animate-in fade-in-50">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
            {/* Left: Article Info & Clean Metadata */}
            <div className="space-y-1.5 min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant="outline"
                  className={
                    directResult.ingested
                      ? directResult.published
                        ? "text-purple-700 bg-purple-50 border-purple-200"
                        : "text-emerald-700 bg-emerald-50 border-emerald-200"
                      : "text-slate-600 bg-slate-100 border-slate-200"
                  }
                >
                  {directResult.ingested
                    ? directResult.published
                      ? "Đã lập chỉ mục AI (RAG)"
                      : "Đã lưu kho tài liệu"
                    : "Chưa lưu vào kho"}
                </Badge>
              </div>

              {/* Title & Original Link */}
              <div>
                <h3 className="text-sm font-semibold text-heading leading-snug line-clamp-2">
                  {directResult.title || directResult.url}
                </h3>
                <a
                  href={directResult.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-2xs text-muted hover:text-brand-primary font-mono truncate max-w-full group"
                  title={directResult.url}
                >
                  <span className="truncate">{directResult.url}</span>
                  <ArrowUpRight className="h-3 w-3 shrink-0 text-muted group-hover:text-brand-primary" />
                </a>
              </div>

              {/* Concise, clean metadata without icon bloat */}
              <div className="flex flex-wrap items-center gap-2 text-2xs text-muted">
                <span>{(directResult.content_length / 1024).toFixed(1)} KB</span>
                <span>·</span>
                <span>
                  {directResult.media_count > 0
                    ? `${directResult.media_count} tệp đính kèm`
                    : "Không có tệp đính kèm"}
                </span>
              </div>
            </div>

            {/* Right: Primary Action Button */}
            {directResult.ingested && (
              <div className="sm:self-center shrink-0">
                <Link
                  href="/admin/documents"
                  className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg border border-border bg-surface text-xs font-medium text-heading hover:bg-surface-hover shadow-xs transition-colors"
                >
                  <span>Xem tài liệu trong kho</span>
                  <ExternalLink className="h-3.5 w-3.5 text-muted" />
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  )
}
