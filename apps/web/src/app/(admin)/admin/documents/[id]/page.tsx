"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft, Layers, Loader2, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import {
  DocumentStatusBadge,
  documentService,
  type DocumentDetail,
} from "@/features/documents"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

interface DocumentDetailPageProps {
  params: Promise<{ id: string }>
}

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const resolvedParams = React.use(params)
  const [doc, setDoc] = React.useState<DocumentDetail | null>(null)
  const [isLoading, setIsLoading] = React.useState(true)

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

  const chunks = doc.chunks || []

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href={ROUTES.ADMIN.DOCUMENTS}>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">Chi tiết Tài liệu</h2>
          <p className="text-xs text-muted">Mã tài liệu: #{resolvedParams.id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Metadata Information */}
        <Card className="h-fit border-border shadow-xs lg:col-span-1">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Thông tin Tài liệu
              </CardTitle>
              <DocumentStatusBadge status={doc.status} />
            </div>
            <CardDescription className="text-xs">
              Metadata bóc tách phục vụ tìm kiếm RAG
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-muted">Tên văn bản:</span>
              <p className="text-xs font-medium text-heading">{doc.title}</p>
            </div>

            <div className="space-y-1">
              <span className="text-[11px] font-semibold text-muted">Danh mục:</span>
              <p className="text-xs font-medium text-heading">{categoryName}</p>
            </div>

            <div className="space-y-2 rounded-lg border border-border bg-surface/50 p-3 text-[11px] text-muted">
              <div className="flex justify-between">
                <span>Tên tệp gốc:</span>
                <span className="font-medium text-heading truncate max-w-44">{doc.file_name}</span>
              </div>
              <div className="flex justify-between">
                <span>Định dạng:</span>
                <span className="font-medium uppercase text-heading">{doc.file_type}</span>
              </div>
              <div className="flex justify-between">
                <span>Kích thước:</span>
                <span className="font-medium text-heading">{fileSizeMB} MB</span>
              </div>
              <div className="flex justify-between">
                <span>Tổng chunks:</span>
                <span className="font-semibold text-brand-primary">
                  {doc.chunk_count ?? chunks.length} chunks
                </span>
              </div>
              <div className="flex justify-between">
                <span>Số trang:</span>
                <span className="font-medium text-heading">
                  {doc.total_pages ?? 1} trang
                </span>
              </div>
              {doc.created_at && (
                <div className="flex justify-between">
                  <span>Ngày tải lên:</span>
                  <span className="font-medium text-heading">
                    {new Date(doc.created_at).toLocaleDateString("vi-VN")}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Chunks Explorer */}
        <Card className="border-border shadow-xs lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-brand-primary" />
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Danh sách Chunks Trích xuất (Vector Chunks: {chunks.length})
              </CardTitle>
            </div>
            <CardDescription className="text-xs">
              Các đoạn văn bản đã bóc tách cấu trúc pháp lý, tạo vector embedding lưu trên Qdrant
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {chunks.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-8 text-center text-xs text-muted">
                <FileText className="mx-auto mb-2 h-6 w-6 text-muted" />
                <p>Tài liệu này chưa có chunks nào được trích xuất (Trạng thái: {doc.status}).</p>
              </div>
            ) : (
              chunks.map((chk, idx) => {
                const chunkIndex = chk.chunk_index ?? idx
                const pageNum = chk.page_number || 1
                const tokens = chk.token_count || 0

                return (
                  <div
                    key={chk.id || idx}
                    className="space-y-2 rounded-lg border border-border bg-surface/50 p-4 text-xs transition-colors hover:bg-surface"
                  >
                    <div className="flex items-center justify-between text-[11px] font-semibold text-muted">
                      <span className="text-brand-primary">
                        Chunk #{chunkIndex + 1}
                      </span>
                      <div className="flex items-center gap-3 text-[11px]">
                        <span>Trang {pageNum}</span>
                        <span>{tokens} tokens</span>
                      </div>
                    </div>
                    <p className="leading-relaxed text-body whitespace-pre-wrap">{chk.content}</p>
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
