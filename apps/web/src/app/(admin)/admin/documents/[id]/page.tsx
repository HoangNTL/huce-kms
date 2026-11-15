"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft, Loader2, FileText, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { DocumentStatusBadge, documentService, type DocumentDetail, type DocumentChunk } from "@/features/documents"
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

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const resolvedParams = React.use(params)
  const [doc, setDoc] = React.useState<DocumentDetail | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)

  React.useEffect(() => {
    documentService
      .getDocument(resolvedParams.id)
      .then((data) => {
        setDoc(data)
      })
      .catch((err) => {
        toast.error("Không thể tải thông tin tài liệu", {
          description: err instanceof Error ? err.message : "Tài liệu không tồn tại.",
        })
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [resolvedParams.id])

  if (isLoading) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-2 text-xs text-muted">
        <Loader2 className="h-6 w-6 animate-spin text-brand-primary" />
        <span>Đang tải thông tin tài liệu #{resolvedParams.id}...</span>
      </div>
    )
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
      : typeof doc.category === "string"
        ? doc.category
        : "Chung"

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
      <div className="border-b border-border pb-2.5">
        <h1 className="font-heading text-xl font-bold tracking-tight text-heading break-words leading-snug">
          {doc.title}
        </h1>
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
                <div className="p-12 text-center text-xs text-muted">
                  <FileText className="mx-auto mb-2 h-8 w-8 text-muted/60" />
                  <p className="font-medium">Tài liệu này chưa có phân đoạn nào được trích xuất.</p>
                  <p className="mt-1 text-[11px]">Trạng thái tài liệu: {doc.status}</p>
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
    </div>
  )
}
