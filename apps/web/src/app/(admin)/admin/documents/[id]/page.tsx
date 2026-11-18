"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft, FileText, Search, Pencil, AlertCircle, ExternalLink, Layers } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
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

interface DocumentDetailPageProps {
  params: Promise<{ id: string }>
}

function ChunkItem({ chunk, index }: { chunk: DocumentChunk; index: number }) {
  const [isExpanded, setIsExpanded] = React.useState(false)
  const isLong = chunk.content.length > 350
  const chunkIndex = chunk.chunk_index ?? index
  const pageNum = chunk.page_number || 1
  const tokens = chunk.token_count || 0

  return (
    <div className="p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 text-xs">
        <span className="font-semibold text-brand-primary">
          Chunk {chunkIndex + 1}
        </span>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span>Trang {pageNum}</span>
          <span>·</span>
          <span>{tokens} tokens</span>
        </div>
      </div>

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
      {/* Top Header Skeleton */}
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

      {/* 2-Column Grid */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
        {/* Left Column (Metadata) */}
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

        {/* Right Column (Chunks) */}
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

  // Load categories for edit modal
  React.useEffect(() => {
    categoryService
      .getCategories()
      .then((cats) => setCategories(cats || []))
      .catch(() => setCategories([]))
  }, [])

  const loadDocument = React.useCallback(async () => {
    try {
      const data = await documentService.getDocument(resolvedParams.id)
      setDoc(data)
    } catch (err) {
      toast.error("Không thể tải thông tin tài liệu", {
        description: err instanceof Error ? err.message : "Tài liệu không tồn tại.",
      })
    } finally {
      setIsLoading(false)
    }
  }, [resolvedParams.id])

  React.useEffect(() => {
    loadDocument()
  }, [loadDocument])

  const handleProcessDocument = async () => {
    setIsProcessing(true)
    try {
      await documentService.processDocument(resolvedParams.id)
      await loadDocument()
      toast.success("Lập chỉ mục tài liệu thành công", {
        description: "Đã phân đoạn và nạp dữ liệu vào hệ thống hỏi đáp AI.",
      })
    } catch (err) {
      toast.error("Lập chỉ mục thất bại", {
        description: err instanceof Error ? err.message : "Vui lòng thử lại sau.",
      })
    } finally {
      setIsProcessing(false)
    }
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

  return (
    <div className="w-full space-y-4">
      {/* 1. Page Header Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-border/60 pb-3">
        <h1 className="font-heading text-lg sm:text-xl font-bold tracking-tight text-heading truncate" title={doc.title}>
          {doc.title}
        </h1>
        <div className="flex items-center gap-2 shrink-0">
          {doc.status === "UPLOADED" && (
            <Button
              onClick={handleProcessDocument}
              loading={isProcessing}
              className="h-8 shrink-0 gap-1.5 rounded-lg text-xs font-medium"
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Lập chỉ mục</span>
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
                <ExternalLink className="h-3.5 w-3.5 text-muted" />
                <span>Xem tệp gốc</span>
              </Button>
            </a>
          )}
          <Button
            variant="outline"
            onClick={() => setIsEditModalOpen(true)}
            className="h-8 shrink-0 gap-1.5 rounded-lg border-border text-xs font-medium text-heading hover:bg-surface-hover hover:text-brand-primary"
          >
            <Pencil className="h-3.5 w-3.5 text-muted" />
            <span>Chỉnh sửa</span>
          </Button>
        </div>
      </div>

      {/* 2. Bố cục 2 cột (Left: 4 cols, Right: 8 cols) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
        {/* Left Column: Metadata Thông tin tài liệu (Sticky khi cuộn) */}
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
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Mã tài liệu</span>
                  <span className="font-medium text-heading">{resolvedParams.id}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Danh mục</span>
                  <span className="max-w-[180px] truncate font-medium text-heading text-right" title={categoryName}>
                    {categoryName}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3 min-w-0">
                  <span className="shrink-0">Tên tệp gốc</span>
                  <span className="max-w-[180px] truncate font-medium text-heading text-right" title={doc.file_name}>
                    {doc.file_name}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Định dạng</span>
                  <span className="font-medium uppercase text-heading">{doc.file_type}</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Kích thước</span>
                  <span className="font-medium text-heading">{fileSizeMB} MB</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Số chunks</span>
                  <span className="font-medium text-heading">
                    {doc.chunk_count ?? allChunks.length}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="shrink-0">Số trang</span>
                  <span className="font-medium text-heading">
                    {doc.total_pages ?? 1} trang
                  </span>
                </div>
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

        {/* Right Column: Chunks Explorer */}
        <div className="space-y-4 lg:col-span-8 xl:col-span-8">
          <Card className="rounded-2xl border border-border bg-surface shadow-xs py-0 gap-0">
            <CardHeader className="border-b border-border px-5 py-3">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-1.5">
                  <CardTitle className="font-heading text-sm font-bold text-heading">
                    Danh sách Chunks
                  </CardTitle>
                  <span className="text-xs font-medium text-muted">
                    ({searchTerm.trim() ? `${filteredChunks.length}/${allChunks.length}` : allChunks.length})
                  </span>
                </div>

                {allChunks.length > 0 && (
                  <div className="relative w-full sm:w-64">
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
              </div>
            </CardHeader>

            <CardContent className="p-0">
              {allChunks.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted">
                  {doc.status.toLowerCase() === "failed" ? (
                    <div className="mx-auto max-w-lg rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-left">
                      <div className="flex items-start gap-3">
                        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
                        <div className="space-y-1">
                          <p className="font-semibold text-destructive">Xử lý tài liệu không thành công</p>
                          <p className="text-xs text-muted leading-relaxed">
                            {doc.error_message || "Tài liệu là file scan/ảnh hoặc không có lớp văn bản điện tử để trích xuất."}
                          </p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center p-8 text-center">
                      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-500">
                        <FileText className="h-5 w-5" />
                      </div>
                      <p className="text-xs font-semibold text-heading">Tài liệu ở trạng thái bản nháp</p>
                      <p className="mt-1 max-w-sm text-2xs text-muted leading-relaxed">
                        Tài liệu đã được lưu trữ an toàn nhưng chưa được phân đoạn và lập chỉ mục tìm kiếm.
                      </p>
                      {doc.status === "UPLOADED" && (
                        <Button
                          size="sm"
                          onClick={handleProcessDocument}
                          loading={isProcessing}
                          className="mt-4 h-8 gap-1.5 rounded-lg text-xs"
                        >
                          <Layers className="h-3.5 w-3.5" />
                          <span>Lập chỉ mục tìm kiếm</span>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              ) : filteredChunks.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted">
                  <p>Không tìm thấy chunk nào khớp với từ khóa &ldquo;{searchTerm}&rdquo;.</p>
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
            </CardContent>
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
          documentService.getDocument(resolvedParams.id).then((data) => setDoc(data))
        }}
      />
    </div>
  )
}
