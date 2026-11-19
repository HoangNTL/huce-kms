"use client"

import * as React from "react"
import Link from "next/link"
import { CheckCircle2, ExternalLink, HelpCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
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
      setDirectResult(res)
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
    <div className="space-y-4">
      <Card className="border-border shadow-xs py-0 gap-0">
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
      </Card>

      {directResult && (
        <Card className="border-border bg-slate-50/50 shadow-xs">
          <CardHeader className="p-4 pb-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <CardTitle className="text-sm font-semibold text-heading">
                Kết quả thu thập
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-4 pt-1 space-y-2 text-xs">
            <div className="flex items-start gap-2">
              <span className="font-medium text-heading shrink-0">Tiêu đề:</span>
              <span className="text-body font-medium">{directResult.title || "—"}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-heading">Kích thước:</span>
              <span className="text-body">
                {(directResult.content_length / 1024).toFixed(1)} KB · {directResult.content_length.toLocaleString()} ký tự
              </span>
            </div>
            {directResult.media_count > 0 && (
              <div className="flex items-center gap-2">
                <span className="font-medium text-heading">Tệp đính kèm:</span>
                <span className="text-body">{directResult.media_count} tệp</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="font-medium text-heading">Trạng thái:</span>
              <Badge
                variant="outline"
                className={
                  directResult.ingested
                    ? autoPublish
                      ? "text-emerald-700 bg-emerald-50 border-emerald-300"
                      : "text-blue-700 bg-blue-50 border-blue-300"
                    : "text-muted border-border"
                }
              >
                {directResult.ingested
                  ? autoPublish
                    ? "Đã lập chỉ mục"
                    : "Bản nháp (Đã lưu)"
                  : "Chưa lưu"}
              </Badge>
            </div>
            {directResult.ingested && (
              <div className="pt-2">
                <Link
                  href="/admin/documents"
                  className="inline-flex items-center gap-1.5 text-xs text-brand-primary font-medium hover:underline"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Xem tài liệu trong kho</span>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
