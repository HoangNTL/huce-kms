"use client"

import * as React from "react"
import Link from "next/link"
import {
  Plus,
  Search,
  Trash2,
  RotateCcw,
  FolderOpen,
  AlertCircle,
  Pencil,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Empty, EmptyHeader, EmptyTitle, EmptyMedia } from "@/components/ui/empty"
import {
  DocumentStatusBadge,
  DocumentUploadModal,
  DocumentEditModal,
  documentService,
  type DocumentMetadata,
} from "@/features/documents"
import { categoryService, type CategoryItem } from "@/features/categories"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { TableSkeleton } from "@/components/shared/table-skeleton"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

const DOCUMENT_STATUS_OPTIONS: Record<string, string> = {
  ALL: "Tất cả trạng thái",
  INDEXED: "Đã lập chỉ mục",
  UPLOADED: "Bản nháp",
  PROCESSING: "Đang xử lý",
  FAILED: "Lỗi",
}

function formatBytes(bytes?: number): string {
  if (!bytes || bytes <= 0) return "0 MB"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
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

  // Delete Confirmation Dialog State
  const [deleteTarget, setDeleteTarget] = React.useState<{ id: string | number; title: string } | null>(null)
  const [isDeleting, setIsDeleting] = React.useState(false)

  // Edit Modal State
  const [editTarget, setEditTarget] = React.useState<DocumentMetadata | null>(null)

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
    categoryService
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
        status: statusFilter !== "ALL" ? statusFilter.toLowerCase() : undefined,
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

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return
    setIsDeleting(true)
    try {
      await documentService.deleteDocument(deleteTarget.id)
      toast.success("Đã xóa tài liệu khỏi kho tri thức", {
        description: `Tài liệu "${deleteTarget.title}" và toàn bộ vector nhúng đã được gỡ bỏ.`,
      })
      setDeleteTarget(null)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Xóa tài liệu thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsDeleting(false)
    }
  }

  const hasActiveFilters = searchTerm !== "" || categoryFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title: Clean & Focused */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
            Quản lý Tài liệu Tri thức
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setIsUploadOpen(true)}
            className="h-8 gap-1.5 rounded-lg bg-brand-primary text-xs font-medium text-white shadow-xs hover:bg-brand-primary-hover"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Tải lên</span>
          </Button>
        </div>
      </div>

      <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0 overflow-hidden">
        {/* Filter toolbar: Perfectly compact with p-4 */}
        <div className="p-4 border-b border-border/50">
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
                className="pl-9 text-xs rounded-lg"
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
                <SelectTrigger className="h-8 min-w-40 rounded-lg text-xs">
                  <SelectValue placeholder="Tất cả danh mục">
                    {(val) => categoryOptions[String(val)] || "Tất cả danh mục"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent align="start" className="min-w-56">
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
                <SelectTrigger className="h-8 min-w-36 rounded-lg text-xs">
                  <SelectValue placeholder="Tất cả trạng thái">
                    {(val) => DOCUMENT_STATUS_OPTIONS[String(val)] || "Tất cả trạng thái"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent align="start" className="min-w-44">
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
                  className="h-8 gap-1 rounded-lg text-xs text-muted hover:text-heading"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Đặt lại</span>
                </Button>
              )}
            </div>
          </div>
        </div>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border/60 bg-slate-50/40 hover:bg-slate-50/40">
                  <TableHead className="w-14 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    STT
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Tên tài liệu
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Danh mục
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Kích thước
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Số chunks
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Trạng thái
                  </TableHead>
                  <TableHead className="text-right text-[11px] font-semibold uppercase tracking-wider text-slate-400 pr-5">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableSkeleton columns={7} rows={6} />
                ) : documents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="py-10 text-center">
                      <Empty className="border-0 p-0">
                        <EmptyMedia variant="icon" className="h-10 w-10 rounded-full bg-slate-100 text-slate-400">
                          <FolderOpen className="h-5 w-5" />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle className="text-sm font-medium text-slate-600">
                            {hasActiveFilters
                              ? "Không tìm thấy tài liệu phù hợp"
                              : "Chưa có tài liệu"}
                          </EmptyTitle>
                        </EmptyHeader>
                      </Empty>
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

                    return (
                      <TableRow
                        key={String(doc.id)}
                        className="transition-colors hover:bg-slate-50/60"
                      >
                        {/* Column STT */}
                        <TableCell className="w-14 text-center text-xs font-medium text-slate-500">
                          {stt}
                        </TableCell>

                        {/* Column Tên tài liệu: Clean Text Link */}
                        <TableCell>
                          <Link
                            href={ROUTES.ADMIN.DOCUMENT_DETAIL(String(doc.id))}
                            className="block max-w-md truncate text-xs font-medium text-heading hover:text-brand-primary hover:underline"
                            title={doc.title}
                          >
                            {doc.title}
                          </Link>
                        </TableCell>

                        {/* Column Danh mục */}
                        <TableCell className="text-xs font-medium text-slate-600">
                          {categoryName}
                        </TableCell>

                        {/* Column Kích thước */}
                        <TableCell className="text-xs font-normal text-slate-500">
                          {formatBytes(doc.file_size)}
                        </TableCell>

                        {/* Column Số chunks: Plain count */}
                        <TableCell className="text-xs font-medium text-slate-600">
                          {doc.chunk_count ?? 0}
                        </TableCell>

                        {/* Column Trạng thái */}
                        <TableCell>
                          <DocumentStatusBadge status={doc.status} />
                        </TableCell>

                        {/* Column Thao tác: Chỉnh sửa, Xóa */}
                        <TableCell className="text-right pr-5">
                          <div className="flex items-center justify-end gap-1">
                            {/* Nút Chỉnh sửa */}
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setEditTarget(doc)}
                              className="h-7 w-7 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                              title="Chỉnh sửa tài liệu"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>

                            {/* Nút Xóa */}
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteTarget({ id: doc.id, title: doc.title })}
                              className="h-7 w-7 rounded-lg text-rose-500 hover:bg-rose-50 hover:text-rose-600"
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
          </div>

          {/* Table Footer with Pagination & Result Count (Automatically hidden when totalItems === 0) */}
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

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-rose-600" />
              <DialogTitle className="font-heading text-lg font-bold text-heading">
                Xóa tài liệu
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted pt-1">
              Tài liệu{" "}
              <strong className="text-heading">&ldquo;{deleteTarget?.title}&rdquo;</strong> và toàn bộ
              dữ liệu liên quan sẽ bị xóa vĩnh viễn.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              Hủy
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={handleConfirmDelete}
              loading={isDeleting}
              loadingText="Đang xóa..."
            >
              Xác nhận
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Document Upload Modal */}
      <DocumentUploadModal
        open={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onSuccess={() => {
          setIsUploadOpen(false)
          setRefreshKey((k) => k + 1)
        }}
      />

      {/* Document Edit Modal */}
      <DocumentEditModal
        open={Boolean(editTarget)}
        onOpenChange={(isOpen) => {
          if (!isOpen) setEditTarget(null)
        }}
        document={editTarget}
        categories={categories}
        onSuccess={() => {
          setEditTarget(null)
          setRefreshKey((k) => k + 1)
        }}
      />
    </div>
  )
}
