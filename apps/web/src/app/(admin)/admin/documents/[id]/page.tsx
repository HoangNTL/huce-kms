"use client"

import * as React from "react"
import Link from "next/link"
import {
  ArrowLeft,
  Search,
  Pencil,
  AlertCircle,
  ExternalLink,
  FileDown,
  Copy,
  Check,
  Image as ImageIcon,
  File,
  Loader2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DocumentStatus,
  DocumentSourceType,
  DocumentStatusBadge,
  DocumentEditModal,
  documentService,
  type DocumentDetail,
  type DocumentChunk,
} from "@/features/documents"
import { categoryService, type CategoryItem } from "@/features/categories"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"
import { API_BASE_URL } from "@/config/env"

interface DocumentDetailPageProps {
  params: Promise<{ id: string }>
}

function ChunkItem({ chunk, index }: { chunk: DocumentChunk; index: number }) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const isLong = chunk.content.length > 350
  const chunkIndex = chunk.chunk_index ?? index
  const pageStart = chunk.page_start ?? chunk.page_number ?? 1
  const pageEnd = chunk.page_end ?? pageStart
  const pageLabel = pageEnd > pageStart ? `Trang ${pageStart}–${pageEnd}` : `Trang ${pageStart}`
  const tokens = chunk.token_count || 0

  return (
    <div className="p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 text-xs">
        <span className="font-semibold text-brand-primary">
          Chunk {chunkIndex + 1}
        </span>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span>{pageLabel}</span>
          <span>·</span>
          <span>{tokens} tokens</span>
        </div>
      </div>

      {chunk.context && (
        <div className="mb-2 rounded-md bg-slate-50 px-2.5 py-1 text-2xs font-medium text-slate-600 border border-slate-200/70">
          {chunk.context}
        </div>
      )}

      <div className="relative">
        <p
          className={`text-sm leading-relaxed text-body whitespace-pre-wrap ${
            !isExpanded && isLong ? "line-clamp-4" : ""
          }`}
        >
          {chunk.content}
        </p>

        {isLong && (
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="cursor-pointer text-xs font-medium text-brand-primary hover:underline"
            >
              {isExpanded ? "Thu gọn" : "Xem thêm"}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function DocumentDetailSkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Skeleton className="h-8 w-24 rounded-lg" />
          <Skeleton className="h-6 w-48" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-24 rounded-lg" />
          <Skeleton className="h-8 w-24 rounded-lg" />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
        <div className="space-y-4 lg:col-span-4">
          <Card className="rounded-2xl border border-border bg-surface p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-5 w-20 rounded-full" />
            </div>
            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-28" />
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-4 lg:col-span-8">
          <Card className="rounded-2xl border border-border bg-surface p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <Skeleton className="h-5 w-36" />
              <Skeleton className="h-8 w-44 rounded-lg" />
            </div>
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border/80 p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                  <Skeleton className="h-3.5 w-full" />
                  <Skeleton className="h-3.5 w-4/5" />
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const resolvedParams = React.use(params)
  const [doc, setDoc] = React.useState<DocumentDetail | null>(null)
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [isEditModalOpen, setIsEditModalOpen] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(true)
  const [isProcessing, setIsProcessing] = React.useState(false)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)

  // Markdown body preview state
  const [markdownBody, setMarkdownBody] = React.useState<string | null>(null)
  const [isLoadingBody, setIsLoadingBody] = React.useState(false)
  const [copied, setCopied] = React.useState(false)

  // Active right tab
  const [activeTab, setActiveTab] = React.useState<string>("chunks")

  // Load categories for edit modal
  React.useEffect(() => {
    categoryService
      .getCategories()
      .then((cats) => setCategories(cats || []))
      .catch(() => setCategories([]))
  }, [])

  // Fetch raw markdown content helper
  const fetchMarkdown = React.useCallback(async (filePath?: string | null, downloadUrl?: string | null) => {
    const targetUrl = filePath
      ? `${API_BASE_URL}/documents/raw/${encodeURIComponent(filePath).replace(/%2F/g, "/")}`
      : downloadUrl

    if (!targetUrl) return
    setIsLoadingBody(true)
    try {
      const res = await fetch(targetUrl)
      if (!res.ok) throw new Error("Could not fetch document content")
      const text = await res.text()
      setMarkdownBody(text)
    } catch {
      setMarkdownBody(null)
    } finally {
      setIsLoadingBody(false)
    }
  }, [])

  // Load document data and optional markdown preview without synchronous setState
  const loadDocumentDetail = React.useCallback(
    async (includePreview: boolean = false, isStale?: () => boolean) => {
      try {
        const data = await documentService.getDocument(resolvedParams.id)
        if (isStale?.()) return
        setDoc(data)
        setIsLoading(false)

        if (includePreview) {
          if ((data.chunk_count || 0) === 0 && data.file_type === "md") {
            setActiveTab("preview")
          }

          if (data.file_type === "md" && (data.file_path || data.download_url)) {
            await fetchMarkdown(data.file_path, data.download_url)
          }
        }
      } catch (err) {
        if (isStale?.()) return
        toast.error("Không thể tải thông tin tài liệu", {
          description: err instanceof Error ? err.message : "Tài liệu không tồn tại.",
        })
        setIsLoading(false)
      }
    },
    [resolvedParams.id, fetchMarkdown]
  )

  // Initial load
  React.useEffect(() => {
    let ignore = false
    void Promise.resolve().then(() => loadDocumentDetail(true, () => ignore))
    return () => {
      ignore = true
    }
  }, [loadDocumentDetail])

  // Auto-refresh while document is still being processed in background
  React.useEffect(() => {
    if (
      !doc ||
      (doc.status !== DocumentStatus.PROCESSING && doc.status !== DocumentStatus.PENDING)
    ) {
      return
    }
    const timer = setInterval(() => {
      void loadDocumentDetail(false)
    }, 3000)
    return () => clearInterval(timer)
  }, [doc, loadDocumentDetail])

  const handleProcessDocument = async () => {
    setIsProcessing(true)
    try {
      await documentService.processDocument(resolvedParams.id)
      await loadDocumentDetail()
      toast.info("Đang lập chỉ mục tài liệu", {
        description: "Hệ thống đang xử lý tài liệu ở chế độ nền, trạng thái sẽ tự cập nhật.",
      })
    } catch (err) {
      toast.error("Lập chỉ mục thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCopyMarkdown = () => {
    if (!markdownBody) return
    navigator.clipboard.writeText(markdownBody)
    setCopied(true)
    toast.success("Đã sao chép nội dung văn bản")
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return <DocumentDetailSkeleton />
  }

  if (!doc) {
    return (
      <div className="space-y-4">
        <Link href={ROUTES.ADMIN.DOCUMENTS}>
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Quay lại danh sách</span>
          </Button>
        </Link>
        <Card className="p-8 text-center text-xs text-muted">
          Không tìm thấy tài liệu có ID #{resolvedParams.id}.
        </Card>
      </div>
    )
  }

  const categoryName =
    typeof doc.category === "object" && doc.category?.name
      ? doc.category.name
      : typeof doc.category === "string" && doc.category.trim()
        ? doc.category
        : "Chưa phân loại"

  const fileSizeMB = doc.file_size
    ? (doc.file_size / 1024 / 1024).toFixed(2)
    : "0.00"

  const allChunks = doc.chunks || []
  const filteredChunks = searchTerm.trim()
    ? allChunks.filter((c) =>
        c.content.toLowerCase().includes(searchTerm.toLowerCase().trim())
      )
    : allChunks

  const startIndex = (currentPage - 1) * pageSize
  const paginatedChunks = filteredChunks.slice(startIndex, startIndex + pageSize)

  // Attachments & Assets
  const relatedDocs = doc.related_documents || []
  const assets = doc.assets || []
  const totalAttachments = relatedDocs.length + assets.length
  const canProcess =
    doc.status === DocumentStatus.UPLOADED ||
    doc.status === DocumentStatus.PENDING ||
    doc.status === DocumentStatus.FAILED
  const isProcessingInBackground =
    doc.status === DocumentStatus.PROCESSING || doc.status === DocumentStatus.PENDING

  let sourceHost = ""
  if (doc.source_url) {
    try {
      sourceHost = new URL(doc.source_url).hostname
    } catch {
      sourceHost = "Xem liên kết"
    }
  }

  return (
    <div className="w-full space-y-4">
      {/* 1. Page Header Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-3">
        <h1
          className="font-heading text-lg sm:text-xl font-bold tracking-tight text-heading truncate min-w-0"
          title={doc.title}
        >
          {doc.title}
        </h1>

        {/* Header Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {canProcess && (
            <Button
              onClick={handleProcessDocument}
              loading={isProcessing}
              className="h-8 shrink-0 rounded-lg text-xs font-semibold bg-brand-primary text-white hover:bg-brand-primary/90 shadow-xs px-3"
              title="Phân đoạn và lập chỉ mục vào kho tri thức AI"
            >
              <span>{doc.status === DocumentStatus.FAILED ? "Xử lý lại" : "Lập chỉ mục"}</span>
            </Button>
          )}

          {doc.download_url && (
            <a
              href={doc.download_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button
                variant="outline"
                className="h-8 gap-1.5 rounded-lg border-border text-xs font-medium text-heading hover:bg-surface-hover"
              >
                <FileDown className="h-3.5 w-3.5 text-muted" />
                <span>Xem tệp gốc</span>
              </Button>
            </a>
          )}

          <Button
            variant="outline"
            onClick={() => setIsEditModalOpen(true)}
            disabled={doc.status === DocumentStatus.PROCESSING}
            title={
              doc.status === DocumentStatus.PROCESSING
                ? "Không thể chỉnh sửa khi tài liệu đang xử lý"
                : "Chỉnh sửa thông tin tài liệu"
            }
            className="h-8 shrink-0 gap-1.5 rounded-lg border-border text-xs font-medium text-heading hover:bg-surface-hover hover:text-brand-primary disabled:opacity-50"
          >
            <Pencil className="h-3.5 w-3.5 text-muted" />
            <span>Chỉnh sửa</span>
          </Button>
        </div>
      </div>

      {/* 2. Main 2-Column Master - Detail Layout */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
        {/* Left Column: Metadata Thông tin tài liệu */}
        <div className="space-y-4 lg:col-span-4 xl:col-span-4 lg:sticky lg:top-0">
          <Card className="rounded-2xl border border-border bg-surface shadow-xs py-0 gap-0">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border px-5 py-3.5">
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Thông tin tài liệu
              </CardTitle>
              <DocumentStatusBadge status={doc.status} />
            </CardHeader>

            <CardContent className="p-5">
              <div className="space-y-3.5 text-xs text-muted">
                {/* Source Origin */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Hình thức</span>
                  <span className="font-medium text-heading">
                    {doc.source_type === DocumentSourceType.CRAWLER
                      ? "Thu thập tự động (Crawler)"
                      : "Tải lên trực tiếp"}
                  </span>
                </div>

                {/* Source Web URL if present */}
                {doc.source_url && (
                  <div className="flex items-center justify-between gap-3">
                    <span className="shrink-0">Nguồn bài viết</span>
                    <a
                      href={doc.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 font-medium text-brand-primary hover:underline truncate max-w-[190px]"
                      title={doc.source_url}
                    >
                      <span className="truncate">{sourceHost}</span>
                      <ExternalLink className="h-3 w-3 shrink-0" />
                    </a>
                  </div>
                )}

                {/* Document ID */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Mã tài liệu</span>
                  <span
                    className="font-mono text-2xs text-heading max-w-[180px] truncate"
                    title={resolvedParams.id}
                  >
                    {resolvedParams.id}
                  </span>
                </div>

                {/* Category */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Danh mục</span>
                  <span
                    className="max-w-[180px] truncate font-medium text-heading text-right"
                    title={categoryName}
                  >
                    {categoryName}
                  </span>
                </div>

                {/* Original Filename */}
                <div className="flex items-center justify-between gap-3 min-w-0">
                  <span className="shrink-0">Tên tệp gốc</span>
                  <span
                    className="max-w-[180px] truncate font-medium text-heading text-right"
                    title={doc.file_name}
                  >
                    {doc.file_name}
                  </span>
                </div>

                {/* Format */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Định dạng</span>
                  <span className="font-medium uppercase text-heading">
                    {doc.file_type}
                  </span>
                </div>

                {/* Size */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Kích thước</span>
                  <span className="font-medium text-heading">{fileSizeMB} MB</span>
                </div>

                {/* Chunks */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Số chunks</span>
                  <span className="font-medium text-heading">
                    {isProcessingInBackground && (doc.chunk_count ?? allChunks.length) === 0
                      ? "—"
                      : (doc.chunk_count ?? allChunks.length)}
                  </span>
                </div>

                {/* Total Pages */}
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Số trang</span>
                  <span className="font-medium text-heading">
                    {isProcessingInBackground && (doc.total_pages ?? 0) === 0
                      ? "—"
                      : `${doc.total_pages ?? 1} trang`}
                  </span>
                </div>

                {/* Attached Files & Assets summary */}
                {totalAttachments > 0 && (
                  <div className="flex items-center justify-between gap-3">
                    <span className="shrink-0">Tệp đính kèm</span>
                    <span className="font-medium text-heading">
                      {relatedDocs.length > 0 && `${relatedDocs.length} PDF `}
                      {assets.length > 0 && `${assets.length} ảnh`}
                    </span>
                  </div>
                )}

                {/* Upload date */}
                {doc.created_at && (
                  <div className="flex items-center justify-between gap-3">
                    <span className="shrink-0">Ngày tải lên</span>
                    <span className="font-medium text-heading">
                      {new Date(doc.created_at).toLocaleDateString("vi-VN")}
                    </span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Tabbed Workspace (Preview, Chunks, Attachments) */}
        <div className="space-y-4 lg:col-span-8 xl:col-span-8">
          <Card className="rounded-2xl border border-border bg-surface shadow-xs py-0 gap-0">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <CardHeader className="border-b border-border px-5 py-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <TabsList className="bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                    <TabsTrigger
                      value="chunks"
                      className="text-xs px-3 py-1 font-medium data-[state=active]:bg-white data-[state=active]:text-heading data-[state=active]:shadow-2xs"
                    >
                      Danh sách Chunks ({allChunks.length})
                    </TabsTrigger>

                    {doc.file_type === "md" && (
                      <TabsTrigger
                        value="preview"
                        className="text-xs px-3 py-1 font-medium data-[state=active]:bg-white data-[state=active]:text-heading data-[state=active]:shadow-2xs"
                      >
                        Nội dung văn bản
                      </TabsTrigger>
                    )}

                    {totalAttachments > 0 && (
                      <TabsTrigger
                        value="attachments"
                        className="text-xs px-3 py-1 font-medium data-[state=active]:bg-white data-[state=active]:text-heading data-[state=active]:shadow-2xs"
                      >
                        Tệp đính kèm ({totalAttachments})
                      </TabsTrigger>
                    )}
                  </TabsList>

                  {activeTab === "chunks" && allChunks.length > 0 && (
                    <div className="relative w-full sm:w-60">
                      <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
                      <Input
                        placeholder="Tìm kiếm chunk..."
                        value={searchTerm}
                        onChange={(e) => {
                          setSearchTerm(e.target.value)
                          setCurrentPage(1)
                        }}
                        className="h-8 rounded-lg pl-8 text-xs"
                      />
                    </div>
                  )}

                  {activeTab === "preview" && markdownBody && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyMarkdown}
                      className="h-7 gap-1 text-xs text-muted hover:text-heading"
                    >
                      {copied ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-600" />
                          <span className="text-emerald-600 font-medium">Đã sao chép</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          <span>Sao chép</span>
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </CardHeader>

              <CardContent className="p-0">
                {/* Tab 1: Danh sách Chunks */}
                <TabsContent value="chunks" className="m-0 focus-visible:outline-none">
                  {allChunks.length === 0 ? (
                    <div className="py-10 px-4 text-center text-xs text-muted">
                      {doc.status === DocumentStatus.FAILED ||
                      String(doc.status).toLowerCase() === "failed" ? (
                        <div className="mx-auto max-w-lg rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-left">
                          <div className="flex items-start gap-3">
                            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                            <div className="space-y-1">
                              <p className="font-semibold text-destructive">
                                Xử lý tài liệu không thành công
                              </p>
                              <p className="text-xs text-muted leading-relaxed">
                                {doc.error_message ||
                                  "Tài liệu là file scan/ảnh hoặc không có lớp văn bản điện tử để trích xuất."}
                              </p>
                            </div>
                          </div>
                        </div>
                      ) : isProcessingInBackground ? (
                        <div className="mx-auto flex max-w-md flex-col items-center gap-2 py-2">
                          <Loader2 className="h-6 w-6 animate-spin text-amber-600" />
                          <p className="text-sm font-medium text-heading">
                            Đang OCR, phân đoạn và lập chỉ mục...
                          </p>
                          <p className="text-xs text-muted leading-relaxed">
                            Hệ thống đang xử lý tài liệu ở chế độ nền. Trang sẽ tự động cập nhật khi hoàn tất.
                          </p>
                        </div>
                      ) : (
                        <p>
                          Chưa có dữ liệu phân đoạn. Bấm <strong className="text-heading font-semibold">Lập chỉ mục</strong> ở trên để phân đoạn.
                        </p>
                      )}
                    </div>
                  ) : filteredChunks.length === 0 ? (
                    <div className="p-8 text-center text-xs text-muted">
                      <p>
                        Không tìm thấy chunk nào khớp với từ khóa &ldquo;{searchTerm}&rdquo;.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="divide-y divide-border/70">
                        {paginatedChunks.map((chk, idx) => (
                          <ChunkItem key={chk.id || idx} chunk={chk} index={startIndex + idx} />
                        ))}
                      </div>

                      {filteredChunks.length > pageSize && (
                        <DataTablePagination
                          currentPage={currentPage}
                          pageSize={pageSize}
                          totalItems={filteredChunks.length}
                          onPageChange={setCurrentPage}
                          onPageSizeChange={(newSize) => {
                            setPageSize(newSize)
                            setCurrentPage(1)
                          }}
                          pageSizeOptions={[5, 10, 20]}
                        />
                      )}
                    </>
                  )}
                </TabsContent>

                {/* Tab 2: Nội dung văn bản (Preview Markdown) */}
                {doc.file_type === "md" && (
                  <TabsContent value="preview" className="m-0 focus-visible:outline-none">
                    {isLoadingBody ? (
                      <div className="p-6 space-y-3">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-4 w-5/6" />
                        <Skeleton className="h-4 w-2/3" />
                      </div>
                    ) : markdownBody ? (
                      <div className="max-h-[600px] overflow-y-auto p-5 text-xs text-body leading-relaxed whitespace-pre-wrap font-sans bg-surface">
                        {markdownBody}
                      </div>
                    ) : (
                      <div className="p-8 text-center text-xs text-muted">
                        Không thể tải nội dung văn bản xem trước.
                      </div>
                    )}
                  </TabsContent>
                )}

                {/* Tab 3: Tệp đính kèm & Ảnh */}
                {totalAttachments > 0 && (
                  <TabsContent value="attachments" className="m-0 p-5 space-y-4 focus-visible:outline-none">
                    {/* 1. Related PDFs */}
                    {relatedDocs.length > 0 && (
                      <div className="space-y-2.5">
                        <h3 className="text-xs font-semibold text-heading flex items-center gap-1.5">
                          <File className="h-3.5 w-3.5 text-rose-500" />
                          <span>Tài liệu PDF đính kèm ({relatedDocs.length})</span>
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {relatedDocs.map((rd) => (
                            <div
                              key={rd.id}
                              className="rounded-xl border border-border p-3 flex items-center justify-between gap-3 bg-surface hover:border-slate-300 transition-colors"
                            >
                              <div className="min-w-0">
                                <Link
                                  href={ROUTES.ADMIN.DOCUMENT_DETAIL(rd.id)}
                                  className="text-xs font-semibold text-heading hover:text-brand-primary truncate block"
                                  title={rd.title}
                                >
                                  {rd.title}
                                </Link>
                                <span className="text-2xs text-muted">
                                  {rd.file_name} · {(rd.file_size / 1024 / 1024).toFixed(2)} MB
                                </span>
                              </div>
                              {rd.download_url && (
                                <a
                                  href={rd.download_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-2xs font-medium text-brand-primary hover:underline shrink-0"
                                >
                                  Tải về ↗
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 2. Image Assets (Scans / Illustrations) */}
                    {assets.length > 0 && (
                      <div className="space-y-2.5">
                        <h3 className="text-xs font-semibold text-heading flex items-center gap-1.5">
                          <ImageIcon className="h-3.5 w-3.5 text-brand-primary" />
                          <span>Hình ảnh & Bản scan ({assets.length})</span>
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                          {assets.map((ast, aIdx) => (
                            <div
                              key={aIdx}
                              className="rounded-xl border border-border p-2.5 space-y-2 bg-surface hover:border-slate-300 transition-colors"
                            >
                              <div className="flex items-center justify-between text-2xs">
                                <span
                                  className="font-medium text-heading truncate max-w-[140px]"
                                  title={ast.file_name}
                                >
                                  {ast.file_name}
                                </span>
                                <a
                                  href={ast.download_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-brand-primary hover:underline inline-flex items-center gap-0.5 shrink-0"
                                >
                                  <span>Xem</span>
                                  <ExternalLink className="h-2.5 w-2.5" />
                                </a>
                              </div>
                              <div className="rounded-lg bg-slate-50 dark:bg-slate-900 border border-border/60 p-1 flex items-center justify-center h-28 overflow-hidden">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src={ast.download_url}
                                  alt={ast.file_name}
                                  className="max-h-full max-w-full object-contain mx-auto"
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </TabsContent>
                )}
              </CardContent>
            </Tabs>
          </Card>
        </div>
      </div>

      {/* Edit Document Modal */}
      <DocumentEditModal
        open={isEditModalOpen}
        onOpenChange={setIsEditModalOpen}
        document={doc}
        categories={categories}
        onSuccess={() => {
          loadDocumentDetail()
        }}
      />
    </div>
  )
}
