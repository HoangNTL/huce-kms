"use client"

import * as React from "react"
import Link from "next/link"
import { FileText, Plus, Search, ExternalLink, Trash2, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
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
import {
  DocumentStatusBadge,
  DocumentUploadModal,
  type DocumentMetadata,
} from "@/features/documents"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

const sampleDocuments: DocumentMetadata[] = [
  {
    id: "doc-01",
    title: "Quy chế đào tạo trình độ đại học chính quy 2024",
    fileName: "quy_che_dao_tao_2024.pdf",
    fileSize: 2450000,
    fileType: "application/pdf",
    category: "Quy chế",
    status: "INDEXED",
    chunkCount: 148,
    createdAt: "2024-03-01",
  },
  {
    id: "doc-02",
    title: "Hướng dẫn thực hiện đồ án tốt nghiệp khóa 65",
    fileName: "huong_dan_do_an_k65.docx",
    fileSize: 1120000,
    fileType: "application/docx",
    category: "Hướng dẫn",
    status: "INDEXED",
    chunkCount: 92,
    createdAt: "2024-03-10",
  },
  {
    id: "doc-03",
    title: "Quyết định mức thu học phí năm học 2024-2025",
    fileName: "qd_hoc_phi_2024.pdf",
    fileSize: 850000,
    fileType: "application/pdf",
    category: "Quy định",
    status: "PROCESSING",
    chunkCount: 0,
    createdAt: "2024-03-15",
  },
]

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = React.useState<DocumentMetadata[]>(sampleDocuments)
  const [isUploadOpen, setIsUploadOpen] = React.useState(false)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [categoryFilter, setCategoryFilter] = React.useState<string>("ALL")
  const [statusFilter, setStatusFilter] = React.useState<string>("ALL")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(5)

  const handleDelete = (id: string, title: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id))
    toast.success("Đã xóa tài liệu khỏi cơ sở tri thức", {
      description: `Tài liệu "${title}" đã được loại bỏ.`,
    })
  }

  const filteredDocs = React.useMemo(() => {
    return documents.filter((d) => {
      const matchSearch =
        d.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
        d.fileName.toLowerCase().includes(searchTerm.toLowerCase())

      const matchCategory = categoryFilter === "ALL" || d.category === categoryFilter
      const matchStatus = statusFilter === "ALL" || d.status === statusFilter

      return matchSearch && matchCategory && matchStatus
    })
  }, [documents, searchTerm, categoryFilter, statusFilter])

  const totalPages = Math.max(1, Math.ceil(filteredDocs.length / pageSize))
  const validPage = Math.min(currentPage, totalPages)

  // Paginated slice
  const paginatedDocs = React.useMemo(() => {
    const start = (validPage - 1) * pageSize
    return filteredDocs.slice(start, start + pageSize)
  }, [filteredDocs, validPage, pageSize])

  const hasActiveFilters = searchTerm !== "" || categoryFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title in Canvas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">Quản lý Tài liệu Tri thức</h2>
          <p className="text-xs text-muted">
            Quản trị kho văn bản nguồn, kiểm soát trạng thái lập chỉ mục Vector và trích xuất chunks
          </p>
        </div>
        <Button
          onClick={() => setIsUploadOpen(true)}
          className="gap-2 bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
        >
          <Plus className="h-4 w-4" />
          <span>Tải lên tài liệu mới</span>
        </Button>
      </div>

      <Card className="border-border shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input with perfect vertical centering */}
            <div className="relative w-full sm:w-80">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Tìm kiếm tài liệu, danh mục..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1)
                }}
                className="pl-9 text-xs"
              />
            </div>

            {/* Filter toolbar */}
            <div className="flex flex-wrap items-center gap-2">
              <Select
                value={categoryFilter}
                onValueChange={(val) => {
                  setCategoryFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả danh mục" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả danh mục</SelectItem>
                  <SelectItem value="Quy chế">Quy chế</SelectItem>
                  <SelectItem value="Hướng dẫn">Hướng dẫn</SelectItem>
                  <SelectItem value="Quy định">Quy định</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={statusFilter}
                onValueChange={(val) => {
                  setStatusFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả trạng thái</SelectItem>
                  <SelectItem value="INDEXED">Đã lập chỉ mục</SelectItem>
                  <SelectItem value="PROCESSING">Đang xử lý</SelectItem>
                  <SelectItem value="FAILED">Lỗi</SelectItem>
                </SelectContent>
              </Select>

              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchTerm("")
                    setCategoryFilter("ALL")
                    setStatusFilter("ALL")
                    setCurrentPage(1)
                  }}
                  className="h-8 gap-1 text-xs text-muted hover:text-heading"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Đặt lại</span>
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14 text-center">STT</TableHead>
                <TableHead>Tên văn bản / Tài liệu</TableHead>
                <TableHead>Danh mục</TableHead>
                <TableHead>Kích thước</TableHead>
                <TableHead>Số chunks</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead className="text-right">Hành động</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedDocs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    Không tìm thấy tài liệu nào phù hợp với bộ lọc hiện tại.
                  </TableCell>
                </TableRow>
              ) : (
                paginatedDocs.map((doc, idx) => {
                  const stt = (currentPage - 1) * pageSize + idx + 1
                  return (
                    <TableRow key={doc.id}>
                      <TableCell className="w-14 text-center font-medium text-muted">
                        {stt}
                      </TableCell>
                      <TableCell className="text-xs font-medium text-heading">
                        <Link
                          href={ROUTES.ADMIN.DOCUMENT_DETAIL(doc.id)}
                          className="flex items-center gap-1.5 hover:text-brand-primary hover:underline"
                        >
                          <FileText className="h-3.5 w-3.5 shrink-0 text-brand-primary" />
                          <span className="max-w-xs truncate">{doc.title}</span>
                        </Link>
                      </TableCell>
                      <TableCell className="text-xs text-muted">{doc.category}</TableCell>
                      <TableCell className="text-xs text-muted">
                        {(doc.fileSize / 1024 / 1024).toFixed(2)} MB
                      </TableCell>
                      <TableCell className="text-xs font-semibold text-heading">
                        {doc.chunkCount}
                      </TableCell>
                      <TableCell>
                        <DocumentStatusBadge status={doc.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link href={ROUTES.ADMIN.DOCUMENT_DETAIL(doc.id)}>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted hover:text-heading"
                              title="Xem chi tiết chunks"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDelete(doc.id, doc.title)}
                            className="h-7 w-7 text-destructive hover:bg-destructive/10"
                            title="Xóa tài liệu"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>

          {/* Table Footer with Pagination & Result Count */}
          <DataTablePagination
            currentPage={validPage}
            pageSize={pageSize}
            totalItems={filteredDocs.length}
            onPageChange={setCurrentPage}
            onPageSizeChange={(newSize) => {
              setPageSize(newSize)
              setCurrentPage(1)
            }}
            pageSizeOptions={[5, 10, 20]}
          />
        </CardContent>
      </Card>

      <DocumentUploadModal
        open={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onSuccess={() => {
          setIsUploadOpen(false)
          toast.success("Tải lên và lập chỉ mục tài liệu thành công")
        }}
      />
    </div>
  )
}
