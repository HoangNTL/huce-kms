"use client"

import * as React from "react"
import {
  ExternalLink,
  Search,
  Copy,
  Check,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { toast } from "@/components/ui/sonner"
import { formatBytes } from "@/lib/utils"
import { categoryService, type CategoryItem } from "@/features/categories"
import { crawlerService, type SessionDetailData, type SessionDetailItem } from "@/features/crawler"

interface SessionDetailPageProps {
  params: Promise<{ id: string }>
}

function formatCompactDate(dateStr?: string | null): string {
  if (!dateStr || dateStr === "—") return "—"
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    const time = d.toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    })
    const date = d.toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    })
    return `${date} ${time}`
  } catch {
    return dateStr
  }
}

function getDomain(urlStr?: string): string {
  if (!urlStr) return ""
  try {
    const u = new URL(urlStr)
    return u.hostname
  } catch {
    return urlStr
  }
}

function truncateFilename(name: string, maxLen = 34): string {
  if (!name || name.length <= maxLen) return name
  const dotIdx = name.lastIndexOf(".")
  const ext = dotIdx > 0 ? name.slice(dotIdx) : ""
  const base = dotIdx > 0 ? name.slice(0, dotIdx) : name
  const keepFront = Math.floor((maxLen - ext.length - 3) * 0.6)
  const keepBack = Math.max(0, maxLen - ext.length - 3 - keepFront)
  return `${base.slice(0, keepFront)}...${base.slice(base.length - keepBack)}${ext}`
}

function cleanMarkdownBody(content?: string): string {
  if (!content) return ""
  // Strip duplicate crawler top metadata header block:
  // # Title \n - **Nguồn:** ... \n - **Ngày crawl:** ... \n ---
  const cleaned = content.replace(/^#\s+[^\n]+\n+(?:- \*\*[^\n]+\n+)*---\s*/, "").trim()
  return cleaned || content
}

export default function SessionDetailPage({ params }: SessionDetailPageProps) {
  const resolvedParams = React.use(params)
  const sessionId = decodeURIComponent(resolvedParams.id)

  const [data, setData] = React.useState<SessionDetailData | null>(null)
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [selectedCategoryId, setSelectedCategoryId] = React.useState<string>("")
  const [isLoading, setIsLoading] = React.useState(true)
  const [isIngestingSession, setIsIngestingSession] = React.useState(false)
  const [isIngestingItem, setIsIngestingItem] = React.useState(false)
  const [isCancelling, setIsCancelling] = React.useState(false)
  const [copied, setCopied] = React.useState(false)

  const [searchQuery, setSearchQuery] = React.useState("")
  const [filterMode, setFilterMode] = React.useState<"ALL" | "INGESTED" | "PDF" | "IMAGE" | "FAILED">("ALL")
  const [selectedIdx, setSelectedIdx] = React.useState(0)
  const [detailTab, setDetailTab] = React.useState<string>("markdown")

  // Load session data
  React.useEffect(() => {
    let ignore = false

    crawlerService
      .getSessionDetails(sessionId)
      .then((res) => {
        if (!ignore) {
          setData(res)
          setIsLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          toast.error("Không thể tải chi tiết phiên thu thập", {
            description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
          })
          setIsLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [sessionId])

  // Periodic polling if session is in progress
  React.useEffect(() => {
    const sessionStatus = String(data?.session?.status || "").toLowerCase()
    if (sessionStatus !== "in_progress" && sessionStatus !== "pending") return

    let isFinished = false
    let intervalId: NodeJS.Timeout | null = null

    const stopPolling = () => {
      isFinished = true
      if (intervalId) {
        clearInterval(intervalId)
        intervalId = null
      }
    }

    const poll = async () => {
      if (isFinished) return
      try {
        const res = await crawlerService.getSessionDetails(sessionId)
        setData(res)
        const updatedStatus = String(res.session?.status || "").toLowerCase()
        if (["completed", "failed", "cancelled", "interrupted"].includes(updatedStatus)) {
          stopPolling()
        }
      } catch {
        // tolerate network blip
      }
    }

    intervalId = setInterval(poll, 2500)

    return () => {
      stopPolling()
    }
  }, [sessionId, data?.session?.status])

  // Cancel running session handler
  const handleCancelSession = async () => {
    if (isCancelling) return
    setIsCancelling(true)
    try {
      await crawlerService.cancelSession(sessionId)
      toast.info("Đã gửi tín hiệu hủy phiên thu thập.")
      const res = await crawlerService.getSessionDetails(sessionId)
      setData(res)
    } catch (err) {
      toast.error("Hủy phiên thu thập thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại.",
      })
    } finally {
      setIsCancelling(false)
    }
  }

  // Load categories
  React.useEffect(() => {
    categoryService
      .getCategories()
      .then((cats) => setCategories(cats || []))
      .catch(() => {
        // Fallback silently if category service is unavailable
      })
  }, [])

  // Ingest entire session
  const handleIngestSession = async () => {
    if (isIngestingSession) return
    setIsIngestingSession(true)
    try {
      await crawlerService.ingest({ session_id: sessionId, auto_publish: true })
      toast.success(`Đã lưu toàn bộ phiên "${sessionId}" vào kho tài liệu`)
      const res = await crawlerService.getSessionDetails(sessionId)
      setData(res)
    } catch (err) {
      toast.error("Lưu vào kho thất bại", {
        description: err instanceof Error ? err.message : "Đã có lỗi xảy ra.",
      })
    } finally {
      setIsIngestingSession(false)
    }
  }

  // Ingest single selected item
  const handleIngestSingleItem = async (pageHash?: string) => {
    if (!pageHash || isIngestingItem) return
    setIsIngestingItem(true)
    try {
      await crawlerService.ingest({
        page_hash: pageHash,
        category_id: selectedCategoryId || undefined,
        auto_publish: true,
      })
      toast.success("Đã nạp bài viết vào kho tài liệu")
      const res = await crawlerService.getSessionDetails(sessionId)
      setData(res)
    } catch (err) {
      toast.error("Lưu bài viết thất bại", {
        description: err instanceof Error ? err.message : "Đã có lỗi xảy ra.",
      })
    } finally {
      setIsIngestingItem(false)
    }
  }

  // Filtered items
  const filteredItems = React.useMemo(() => {
    if (!data?.items) return []
    return data.items.filter((item: SessionDetailItem) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const matchesTitle = item.title.toLowerCase().includes(q)
        const matchesUrl = item.url.toLowerCase().includes(q)
        if (!matchesTitle && !matchesUrl) return false
      }

      if (filterMode === "INGESTED") return Boolean(item.is_ingested)
      if (filterMode === "PDF") return item.pdf_count > 0
      if (filterMode === "IMAGE") return item.image_count > 0
      if (filterMode === "FAILED") return item.status !== "success"
      return true
    })
  }, [data, searchQuery, filterMode])

  // Current selected item
  const selectedItem = filteredItems[selectedIdx] ?? filteredItems[0] ?? null

  // Derive active tab safely without setState in effect
  const activeDetailTab =
    detailTab === "pdfs" && (selectedItem?.pdf_count || 0) === 0
      ? "markdown"
      : detailTab === "images" && (selectedItem?.image_count || 0) === 0
      ? "markdown"
      : detailTab

  // Copy markdown handler
  const handleCopyMarkdown = () => {
    if (!selectedItem?.markdown_content) return
    navigator.clipboard.writeText(cleanMarkdownBody(selectedItem.markdown_content))
    setCopied(true)
    toast.success("Đã sao chép nội dung văn bản")
    setTimeout(() => setCopied(false), 2000)
  }

  // Aggregate stats
  const totalItems = data?.items?.length || 0
  const ingestedCount = data?.items?.filter((i) => i.is_ingested).length || 0
  const remainingCount = totalItems - ingestedCount
  const pdfItemsCount = data?.items?.filter((i) => i.pdf_count > 0).length || 0
  const imageItemsCount = data?.items?.filter((i) => i.image_count > 0).length || 0
  const failedItemsCount = data?.items?.filter((i) => i.status !== "success").length || 0
  const sessionStartTime = String(data?.session?.started_at || data?.session?.created_at || "")
  const sessionStatus = String(data?.session?.status || "completed").toLowerCase()
  const totalUrls = Number(data?.session?.total_urls || totalItems)
  const completedUrls = Number(data?.session?.completed_urls || totalItems)
  const isRunning = sessionStatus === "in_progress" || sessionStatus === "pending"

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div className="space-y-1">
            <Skeleton className="h-6 w-56" />
            <Skeleton className="h-4 w-40" />
          </div>
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
          <div className="space-y-3 lg:col-span-5">
            <Skeleton className="h-9 w-full rounded-lg" />
            <div className="flex gap-2">
              <Skeleton className="h-7 w-16 rounded-md" />
              <Skeleton className="h-7 w-16 rounded-md" />
            </div>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))}
          </div>
          <div className="space-y-4 lg:col-span-7">
            <Skeleton className="h-64 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 1. Header Bar: Clean, Unified & Professional */}
      <div className="flex flex-col gap-2 border-b border-border/60 pb-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
                Phiên <span className="font-mono text-brand-primary">{sessionId}</span>
              </h1>
              {isRunning ? (
                <Badge
                  variant="outline"
                  className="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 border-blue-200 font-medium"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
                  <span>Đang chạy ({completedUrls}/{totalUrls})</span>
                </Badge>
              ) : sessionStatus === "completed" ? (
                <Badge
                  variant="outline"
                  className="text-emerald-700 bg-emerald-50 border-emerald-200 font-medium"
                >
                  Hoàn thành
                </Badge>
              ) : sessionStatus === "cancelled" ? (
                <Badge
                  variant="outline"
                  className="text-slate-600 bg-slate-100 border-slate-200 font-medium"
                >
                  Đã hủy
                </Badge>
              ) : sessionStatus === "interrupted" ? (
                <Badge
                  variant="outline"
                  className="text-amber-700 bg-amber-50 border-amber-200 font-medium"
                >
                  Bị gián đoạn
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="text-rose-700 bg-rose-50 border-rose-200 font-medium"
                >
                  Thất bại
                </Badge>
              )}
            </div>
            <p className="mt-0.5 text-xs text-muted">
              {formatCompactDate(sessionStartTime)} · {totalItems} bài đã thu thập · {ingestedCount} đã lưu
            </p>
          </div>

          <div className="flex items-center gap-2">
            {isRunning && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleCancelSession}
                disabled={isCancelling}
                loading={isCancelling}
                className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200 shadow-xs px-3"
              >
                <span>Hủy phiên</span>
              </Button>
            )}

            {!isRunning && totalItems > 0 && (
              remainingCount === 0 ? (
                <div className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-3 py-1.5 rounded-lg">
                  <Check className="h-3.5 w-3.5" />
                  <span>Đã lưu toàn bộ</span>
                </div>
              ) : (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleIngestSession}
                  disabled={isIngestingSession}
                  loading={isIngestingSession}
                  className="bg-brand-primary text-white hover:bg-brand-primary/90 text-xs font-semibold shadow-xs"
                >
                  <span>
                    {ingestedCount > 0 ? `Lưu ${remainingCount} bài còn lại` : "Lưu tất cả"}
                  </span>
                </Button>
              )
            )}
          </div>
        </div>

        {isRunning && totalUrls > 0 && (
          <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-brand-primary h-1.5 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, Math.round((completedUrls / totalUrls) * 100))}%`,
              }}
            />
          </div>
        )}
      </div>

      {/* 2. Main Master - Detail Layout */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
        {/* Left Column (Master: List of Articles) */}
        <div className="space-y-3 lg:col-span-5">
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted" />
            <Input
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value)
                setSelectedIdx(0)
              }}
              placeholder="Tìm kiếm theo tiêu đề, liên kết..."
              className="pl-9 h-9 text-xs bg-surface"
            />
          </div>

          {/* Clean Segmented Filter Tabs */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs w-fit">
            <button
              type="button"
              onClick={() => {
                setFilterMode("ALL")
                setSelectedIdx(0)
              }}
              className={`px-3 py-1 rounded-md transition-all font-medium cursor-pointer ${
                filterMode === "ALL"
                  ? "bg-white dark:bg-slate-900 text-heading shadow-2xs font-semibold"
                  : "text-muted hover:text-heading"
              }`}
            >
              Tất cả ({totalItems})
            </button>

            {ingestedCount > 0 && ingestedCount < totalItems && (
              <button
                type="button"
                onClick={() => {
                  setFilterMode("INGESTED")
                  setSelectedIdx(0)
                }}
                className={`px-3 py-1 rounded-md transition-all font-medium cursor-pointer ${
                  filterMode === "INGESTED"
                    ? "bg-white dark:bg-slate-900 text-heading shadow-2xs font-semibold"
                    : "text-muted hover:text-heading"
                }`}
              >
                Đã lưu ({ingestedCount})
              </button>
            )}

            {pdfItemsCount > 0 && (
              <button
                type="button"
                onClick={() => {
                  setFilterMode("PDF")
                  setSelectedIdx(0)
                }}
                className={`px-3 py-1 rounded-md transition-all font-medium cursor-pointer ${
                  filterMode === "PDF"
                    ? "bg-white dark:bg-slate-900 text-heading shadow-2xs font-semibold"
                    : "text-muted hover:text-heading"
                }`}
              >
                Có PDF ({pdfItemsCount})
              </button>
            )}

            {imageItemsCount > 0 && (
              <button
                type="button"
                onClick={() => {
                  setFilterMode("IMAGE")
                  setSelectedIdx(0)
                }}
                className={`px-3 py-1 rounded-md transition-all font-medium cursor-pointer ${
                  filterMode === "IMAGE"
                    ? "bg-white dark:bg-slate-900 text-heading shadow-2xs font-semibold"
                    : "text-muted hover:text-heading"
                }`}
              >
                Có ảnh ({imageItemsCount})
              </button>
            )}

            {failedItemsCount > 0 && (
              <button
                type="button"
                onClick={() => {
                  setFilterMode("FAILED")
                  setSelectedIdx(0)
                }}
                className={`px-3 py-1 rounded-md transition-all font-medium cursor-pointer ${
                  filterMode === "FAILED"
                    ? "bg-white dark:bg-slate-900 text-rose-600 shadow-2xs font-semibold"
                    : "text-rose-600/80 hover:text-rose-700"
                }`}
              >
                Lỗi ({failedItemsCount})
              </button>
            )}
          </div>

          {/* Cards List: Clean & Compact Specification */}
          <div className="space-y-2 max-h-[calc(100vh-210px)] overflow-y-auto pr-1">
            {filteredItems.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted">
                Không tìm thấy bài viết nào phù hợp.
              </div>
            ) : (
              filteredItems.map((item, idx) => {
                const isSelected = selectedItem === item
                const isSuccess = item.status === "success"

                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedIdx(idx)}
                    className={`cursor-pointer rounded-xl border p-3 transition-all ${
                      isSelected
                        ? "border-brand-primary bg-brand-primary/5 shadow-xs ring-1 ring-brand-primary/30"
                        : "border-border/70 bg-surface hover:border-slate-300 hover:bg-slate-50/50"
                    }`}
                  >
                    <div className="space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-xs font-semibold leading-snug text-heading line-clamp-2 flex-1">
                          {item.title || item.url}
                        </h3>
                        {!isSuccess && (
                          <span className="shrink-0 text-3xs font-semibold text-rose-600 bg-rose-50 border border-rose-200 px-1.5 py-0.5 rounded">
                            Lỗi
                          </span>
                        )}
                      </div>

                      {/* Bottom row: domain + clean meta tags */}
                      <div className="flex items-center justify-between text-2xs text-muted pt-0.5">
                        <span className="truncate max-w-[140px] font-mono text-slate-500" title={item.url}>
                          {getDomain(item.url)}
                        </span>

                        <div className="flex items-center gap-1.5 shrink-0">
                          {item.pdf_count > 0 && (
                            <span className="text-2xs text-slate-600 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded font-mono font-medium">
                              {item.pdf_count} PDF
                            </span>
                          )}
                          {item.image_count > 0 && (
                            <span className="text-2xs text-slate-600 bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded font-mono font-medium">
                              {item.image_count} ảnh
                            </span>
                          )}
                          {item.is_ingested && (
                            <span className="text-2xs text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-1.5 py-0.5 rounded font-medium">
                              Đã lưu
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Right Column (Detail: Inspector Panel & Ingestion Action) */}
        <div className="lg:col-span-7">
          {selectedItem ? (
            <Card className="rounded-2xl border border-border bg-surface shadow-xs overflow-hidden">
              {/* Header: Title, clean domain link, and action row */}
              <div className="p-4 border-b border-border/70 space-y-3">
                <div>
                  <h2 className="text-base font-bold text-heading leading-snug">
                    {selectedItem.title || selectedItem.url}
                  </h2>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted">
                    <a
                      href={selectedItem.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 font-mono text-xs text-slate-500 hover:text-brand-primary"
                      title={selectedItem.url}
                    >
                      <span>{getDomain(selectedItem.url)}</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                    {selectedItem.status !== "success" && (
                      <span className="text-rose-600 font-medium">• Lỗi bóc tách</span>
                    )}
                  </div>
                </div>

                {/* Action row: Category + "Lưu bài này" */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-border/50">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs text-muted shrink-0">Danh mục:</span>
                    <select
                      value={selectedCategoryId}
                      onChange={(e) => setSelectedCategoryId(e.target.value)}
                      disabled={selectedItem.is_ingested}
                      className="h-8 rounded-lg border border-border bg-white dark:bg-slate-900 px-2.5 text-xs text-heading focus:border-brand-primary focus:outline-none"
                    >
                      <option value="">Chưa phân loại</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    {selectedItem.is_ingested ? (
                      <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600">
                        <Check className="h-4 w-4" />
                        <span>Đã lưu vào kho</span>
                      </span>
                    ) : (
                      <Button
                        variant="default"
                        size="sm"
                        onClick={() => handleIngestSingleItem(selectedItem.page_hash)}
                        loading={isIngestingItem}
                        disabled={!selectedItem.page_hash}
                        className="bg-brand-primary text-white hover:bg-brand-primary/90 text-xs font-semibold shadow-xs"
                      >
                        <span>Lưu bài này</span>
                      </Button>
                    )}
                  </div>
                </div>
              </div>

              {/* Inspection Tabs: Dynamic (hide tabs with 0 count) */}
              <div className="p-4 pt-3 w-full">
                <Tabs
                  value={activeDetailTab}
                  onValueChange={setDetailTab}
                  className="flex flex-col w-full gap-3"
                >
                  <div className="flex items-center justify-between border-b border-border pb-2.5">
                    <TabsList className="bg-slate-100 dark:bg-slate-800 p-1">
                      <TabsTrigger value="markdown" className="text-xs px-3 py-1 font-medium">
                        Văn bản
                      </TabsTrigger>
                      {selectedItem.pdf_count > 0 && (
                        <TabsTrigger value="pdfs" className="text-xs px-3 py-1 font-medium">
                          PDF ({selectedItem.pdf_count})
                        </TabsTrigger>
                      )}
                      {selectedItem.image_count > 0 && (
                        <TabsTrigger value="images" className="text-xs px-3 py-1 font-medium">
                          Ảnh ({selectedItem.image_count})
                        </TabsTrigger>
                      )}
                    </TabsList>

                    {detailTab === "markdown" && selectedItem.markdown_content && (
                      <Button
                        variant="outline"
                        size="xs"
                        onClick={handleCopyMarkdown}
                        className="gap-1 text-xs"
                      >
                        {copied ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                        <span>{copied ? "Đã chép" : "Sao chép"}</span>
                      </Button>
                    )}
                  </div>

                  {/* Tab 1: Markdown Content */}
                  <TabsContent value="markdown" className="w-full">
                    {selectedItem.markdown_content ? (
                      <div className="rounded-xl border border-border bg-slate-50/50 p-4 max-h-[550px] overflow-y-auto">
                        <pre className="font-mono text-xs leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words">
                          {cleanMarkdownBody(selectedItem.markdown_content)}
                        </pre>
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-border p-12 text-center text-xs text-muted">
                        Không có nội dung văn bản.
                      </div>
                    )}
                  </TabsContent>

                  {/* Tab 2: Attached PDFs */}
                  {selectedItem.pdf_count > 0 && (
                    <TabsContent value="pdfs" className="w-full space-y-2">
                      <div className="grid grid-cols-1 gap-2">
                        {selectedItem.pdfs.map((pdf, pIdx) => {
                          const fullUrl = pdf.url ? crawlerService.getMediaUrl(pdf.url) : null

                          return (
                            <div
                              key={pIdx}
                              className="flex items-center justify-between gap-3 rounded-xl border border-border bg-white dark:bg-slate-900 p-3 transition-colors hover:border-slate-300"
                            >
                              <div className="flex items-center gap-2.5 min-w-0">
                                <span className="text-2xs font-bold text-rose-600 bg-rose-50 border border-rose-200/70 px-1.5 py-0.5 rounded shrink-0">
                                  PDF
                                </span>
                                <div className="min-w-0">
                                  <p className="text-xs font-medium text-heading truncate" title={pdf.name}>
                                    {truncateFilename(pdf.name, 36)}
                                  </p>
                                  <span className="text-2xs text-muted">{formatBytes(pdf.size)}</span>
                                </div>
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                {fullUrl && (
                                  <a href={fullUrl} target="_blank" rel="noreferrer">
                                    <Button variant="outline" size="xs" className="gap-1.5 text-xs">
                                      <span>Xem tệp PDF</span>
                                      <ExternalLink className="h-3 w-3 text-muted" />
                                    </Button>
                                  </a>
                                )}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </TabsContent>
                  )}

                  {/* Tab 3: Crawled Images (Document Scans) */}
                  {selectedItem.image_count > 0 && (
                    <TabsContent value="images" className="w-full space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                        {selectedItem.images.map((img, iIdx) => {
                          const fullUrl = img.url ? crawlerService.getMediaUrl(img.url) : null
                          const pageLabel = selectedItem.image_count > 1 ? `Trang ${iIdx + 1}` : "Tài liệu scan"

                          return (
                            <div
                              key={iIdx}
                              className="rounded-xl border border-border bg-white dark:bg-slate-900 p-3 space-y-2.5 transition-colors hover:border-slate-300"
                            >
                              {/* Header: Page info & Clear direct action */}
                              <div className="flex items-center justify-between text-xs">
                                <div className="flex items-center gap-1.5 min-w-0">
                                  <span className="font-semibold text-heading text-xs">
                                    {pageLabel}
                                  </span>
                                  <span className="text-2xs text-muted">
                                    · {formatBytes(img.size)}
                                  </span>
                                </div>
                                {fullUrl && (
                                  <a
                                    href={fullUrl}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 text-2xs font-medium text-brand-primary hover:underline shrink-0"
                                  >
                                    <span>Xem ảnh gốc</span>
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                              </div>

                              {/* Document Sheet Preview: clean, non-scrollable, fit-height paper look */}
                              {fullUrl ? (
                                <div className="rounded-lg border border-slate-200/90 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-950/40 p-2 flex items-center justify-center">
                                  <div className="rounded bg-white dark:bg-slate-900 shadow-2xs p-1 flex items-center justify-center w-full">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                      src={fullUrl}
                                      alt={img.name}
                                      className="max-h-[500px] w-auto max-w-full object-contain mx-auto"
                                    />
                                  </div>
                                </div>
                              ) : (
                                <div className="h-40 bg-slate-50 rounded-lg flex items-center justify-center text-xs text-muted">
                                  Không thể tải ảnh
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </TabsContent>
                  )}
                </Tabs>
              </div>
            </Card>
          ) : (
            <div className="rounded-2xl border border-dashed border-border p-16 text-center text-xs text-muted">
              Chọn một bài viết ở danh sách bên trái để kiểm tra chi tiết.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
