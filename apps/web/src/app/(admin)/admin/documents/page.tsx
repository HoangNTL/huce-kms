"use client"

import * as React from "react"
import Link from "next/link"
import { FileText, Plus, Search, ExternalLink, Trash2, RotateCcw, Loader2 } from "lucide-react"
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
  documentService,
  type DocumentMetadata,
  type CategoryItem,
} from "@/features/documents"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

const DOCUMENT_STATUS_OPTIONS: Record<string, string> = {
  ALL: "Tất cả trạng thái",
  INDEXED: "Đã lập chỉ mục",
  UPLOADED: "Bản nháp",
  PROCESSING: "Đang xử lý",
  FAILED: "Lỗi",
}

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = React.useState<DocumentMetadata[]>([])
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [isUploadOpen, setIsUploadOpen] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [categoryFilter, setCategoryFilter] = React.useState<string>("ALL")
  const [statusFilter, setStatusFilter] = React.useState<string>("ALL")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)
  const [totalItems, setTotalItems] = React.useState(0)
  const [refreshKey, setRefreshKey] = React.useState(0)

  const categoryOptions: Record<string, string> = React.useMemo(() => {
    const map: Record<string, string> = { ALL: "Tất cả danh mục" }
    for (const cat of categories) {
      map[String(cat.id)] = cat.name
    }
    return map
  }, [categories])

  // Load categories once
  React.useEffect(() => {
    let ignore = false
    documentService
      .getCategories()
      .then((cats) => {
        if (!ignore) setCategories(cats || [])
      })
      .catch(() => {
        if (!ignore) setCategories([])
      })
    return () => {
      ignore = true
    }
  }, [])

  // Fetch documents from real API
  React.useEffect(() => {
    let ignore = false
    documentService
      .getDocuments({
        page: currentPage,
        pageSize,
        search: searchTerm.trim() || undefined,
        category_id: categoryFilter !== "ALL" ? categoryFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      })
      .then((res) => {
        if (!ignore) {
          setDocuments(res.items)
          setTotalItems(res.total)
          setIsLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          toast.error("Không thể tải danh sách tài liệu", {
            description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
          })
          setIsLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [currentPage, pageSize, searchTerm, categoryFilter, statusFilter, refreshKey])

  const handleDelete = async (id: string | number, title: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa tài liệu "${title}" và toàn bộ vector embeddings liên quan không?`)) {
      return
    }

    try {
      await documentService.deleteDocument(id)
      toast.success("Đã xóa tài liệu khỏi cơ sở tri thức", {
        description: `Tài liệu "${title}" đã được loại bỏ hoàn toàn.`,
      })
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Xóa tài liệu thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    }
  }

  const hasActiveFilters = searchTerm !== "" || categoryFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title in Canvas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">Quản lý Tài liệu Tri thức</h2>
          <p className="text-xs text-muted">
            Quản trị kho văn bản nguồn, kiểm soát trạng thái lập chỉ mục Vector và trích xuất chunks ({totalItems} tài liệu)
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
            {/* Search Input */}
            <div className="relative w-full sm:w-80">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Tìm kiếm tài liệu..."
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
                items={categoryOptions}
                value={categoryFilter}
                onValueChange={(val) => {
                  setCategoryFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả danh mục">
                    {(val) => categoryOptions[String(val)] || "Tất cả danh mục"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả danh mục</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={String(cat.id)} value={String(cat.id)}>
                      {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select
                items={DOCUMENT_STATUS_OPTIONS}
                value={statusFilter}
                onValueChange={(val) => {
                  setStatusFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả trạng thái">
                    {(val) => DOCUMENT_STATUS_OPTIONS[String(val)] || "Tất cả trạng thái"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả trạng thái</SelectItem>
                  <SelectItem value="INDEXED">Đã lập chỉ mục</SelectItem>
                  <SelectItem value="UPLOADED">Bản nháp</SelectItem>
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
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                      <span>Đang tải danh sách tài liệu từ cơ sở dữ liệu...</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : documents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    Không tìm thấy tài liệu nào phù hợp với bộ lọc hiện tại.
                  </TableCell>
                </TableRow>
              ) : (
                documents.map((doc, idx) => {
                  const stt = (currentPage - 1) * pageSize + idx + 1
                  const categoryName =
                    typeof doc.category === "object" && doc.category?.name
                      ? doc.category.name
                      : typeof doc.category === "string"
                        ? doc.category
                        : "Chung"
                  const file_size_mb = doc.file_size
                    ? (doc.file_size / 1024 / 1024).toFixed(2)
                    : "0.00"

                  return (
                    <TableRow key={String(doc.id)}>
                      <TableCell className="w-14 text-center font-medium text-muted">
                        {stt}
                      </TableCell>
                      <TableCell className="text-xs font-medium text-heading">
                        <Link
                          href={ROUTES.ADMIN.DOCUMENT_DETAIL(String(doc.id))}
                          className="flex items-center gap-1.5 hover:text-brand-primary hover:underline"
                        >
                          <FileText className="h-3.5 w-3.5 shrink-0 text-brand-primary" />
                          <span className="max-w-xs truncate">{doc.title}</span>
                        </Link>
                      </TableCell>
                      <TableCell className="text-xs text-muted">{categoryName}</TableCell>
                      <TableCell className="text-xs text-muted">{file_size_mb} MB</TableCell>
                      <TableCell className="text-xs font-semibold text-heading">
                        {doc.chunk_count ?? 0}
                      </TableCell>
                      <TableCell>
                        <DocumentStatusBadge status={doc.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link href={ROUTES.ADMIN.DOCUMENT_DETAIL(String(doc.id))}>
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
            currentPage={currentPage}
            pageSize={pageSize}
            totalItems={totalItems}
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
          setRefreshKey((k) => k + 1)
        }}
      />
    </div>
  )
}
