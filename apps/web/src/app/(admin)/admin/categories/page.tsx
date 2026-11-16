"use client"

import * as React from "react"
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  RotateCcw,
  AlertCircle,
  FolderOpen,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Empty, EmptyHeader, EmptyTitle, EmptyMedia } from "@/components/ui/empty"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { TableSkeleton } from "@/components/shared/table-skeleton"
import { toast } from "@/components/ui/sonner"
import { documentService, type CategoryItem } from "@/features/documents"

export default function AdminCategoriesPage() {
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)
  const [refreshKey, setRefreshKey] = React.useState(0)

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = React.useState(false)
  const [createName, setCreateName] = React.useState("")
  const [createSlug, setCreateSlug] = React.useState("")
  const [createDescription, setCreateDescription] = React.useState("")
  const [isCreating, setIsCreating] = React.useState(false)

  // Edit Modal State
  const [editTarget, setEditTarget] = React.useState<CategoryItem | null>(null)
  const [editName, setEditName] = React.useState("")
  const [editSlug, setEditSlug] = React.useState("")
  const [editDescription, setEditDescription] = React.useState("")
  const [isUpdating, setIsUpdating] = React.useState(false)

  // Delete Modal State
  const [deleteTarget, setDeleteTarget] = React.useState<CategoryItem | null>(null)
  const [isDeleting, setIsDeleting] = React.useState(false)

  // Fetch Categories
  React.useEffect(() => {
    let ignore = false
    documentService
      .getCategories()
      .then((data) => {
        if (!ignore) {
          setCategories(data || [])
          setIsLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          toast.error("Không thể tải danh sách danh mục", {
            description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
          })
          setIsLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [refreshKey])

  // Open Edit Modal
  const handleOpenEdit = (cat: CategoryItem) => {
    setEditTarget(cat)
    setEditName(cat.name)
    setEditSlug(cat.slug || "")
    setEditDescription(cat.description || "")
  }

  // Create Category Handler
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedName = createName.trim()
    if (!trimmedName || trimmedName.length < 2) {
      toast.error("Tên danh mục không hợp lệ", {
        description: "Tên danh mục phải có ít nhất 2 ký tự.",
      })
      return
    }

    try {
      setIsCreating(true)
      await documentService.createCategory({
        name: trimmedName,
        slug: createSlug.trim() || undefined,
        description: createDescription.trim() || undefined,
      })
      toast.success("Tạo danh mục thành công!", {
        description: `Danh mục "${trimmedName}" đã được tạo.`,
      })
      setIsCreateOpen(false)
      setCreateName("")
      setCreateSlug("")
      setCreateDescription("")
      setIsLoading(true)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Tạo danh mục thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsCreating(false)
    }
  }

  // Update Category Handler
  const handleUpdateCategory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editTarget) return
    const trimmedName = editName.trim()
    if (!trimmedName || trimmedName.length < 2) {
      toast.error("Tên danh mục không hợp lệ", {
        description: "Tên danh mục phải có ít nhất 2 ký tự.",
      })
      return
    }

    try {
      setIsUpdating(true)
      await documentService.updateCategory(editTarget.id, {
        name: trimmedName,
        slug: editSlug.trim() || undefined,
        description: editDescription.trim() ? editDescription.trim() : "",
      })
      toast.success("Cập nhật danh mục thành công!", {
        description: `Danh mục "${trimmedName}" đã được cập nhật.`,
      })
      setEditTarget(null)
      setIsLoading(true)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Cập nhật danh mục thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsUpdating(false)
    }
  }

  // Delete Category Handler
  const handleDeleteCategory = async () => {
    if (!deleteTarget) return
    try {
      setIsDeleting(true)
      await documentService.deleteCategory(deleteTarget.id)
      toast.success("Xóa danh mục thành công!", {
        description: `Đã xóa danh mục "${deleteTarget.name}".`,
      })
      setDeleteTarget(null)
      if (paginatedCategories.length === 1 && currentPage > 1) {
        setCurrentPage((p) => p - 1)
      }
      setIsLoading(true)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Xóa danh mục thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsDeleting(false)
    }
  }

  // Filter Categories
  const filteredCategories = React.useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    if (!term) return categories
    return categories.filter(
      (c) =>
        c.name.toLowerCase().includes(term) ||
        (c.slug && c.slug.toLowerCase().includes(term)) ||
        (c.description && c.description.toLowerCase().includes(term))
    )
  }, [categories, searchTerm])

  const totalItems = filteredCategories.length
  const startIndex = (currentPage - 1) * pageSize
  const paginatedCategories = filteredCategories.slice(startIndex, startIndex + pageSize)
  const hasActiveFilters = searchTerm.trim() !== ""

  return (
    <div className="space-y-6">
      {/* Page Title: Clean & Focused */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
            Quản lý Danh mục
          </h1>
        </div>
        <Button
          onClick={() => setIsCreateOpen(true)}
          className="h-8 gap-1.5 rounded-lg bg-brand-primary text-xs font-medium text-white shadow-xs hover:bg-brand-primary-hover"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>Thêm danh mục</span>
        </Button>
      </div>

      <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0 overflow-hidden">
        {/* Filter toolbar: Perfectly compact with p-4 */}
        <div className="p-4 border-b border-border/50">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input */}
            <div className="relative w-full sm:w-80">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Tìm kiếm danh mục..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1)
                }}
                className="pl-9 text-xs rounded-lg"
              />
            </div>

            {/* Filter toolbar reset button */}
            <div className="flex flex-wrap items-center gap-2">
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchTerm("")
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
                    Tên danh mục
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Đường dẫn
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Mô tả
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Ngày tạo
                  </TableHead>
                  <TableHead className="text-right text-[11px] font-semibold uppercase tracking-wider text-slate-400 pr-5">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableSkeleton columns={6} rows={5} />
                ) : filteredCategories.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="py-10 text-center">
                      <Empty className="border-0 p-0">
                        <EmptyMedia variant="icon" className="h-10 w-10 rounded-full bg-slate-100 text-slate-400">
                          <FolderOpen className="h-5 w-5" />
                        </EmptyMedia>
                        <EmptyHeader>
                          <EmptyTitle className="text-sm font-medium text-slate-600">
                            {hasActiveFilters
                              ? "Không tìm thấy danh mục phù hợp"
                              : "Chưa có danh mục"}
                          </EmptyTitle>
                        </EmptyHeader>
                      </Empty>
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedCategories.map((cat, idx) => {
                    const stt = (currentPage - 1) * pageSize + idx + 1

                    return (
                      <TableRow
                        key={String(cat.id)}
                        className="transition-colors hover:bg-slate-50/60"
                      >
                        {/* Column STT */}
                        <TableCell className="w-14 text-center text-xs font-medium text-slate-500">
                          {stt}
                        </TableCell>

                        {/* Column Tên danh mục */}
                        <TableCell className="font-medium text-xs text-slate-800">
                          <span className="font-semibold text-heading">{cat.name}</span>
                        </TableCell>

                        {/* Column Đường dẫn: Clean font-mono text without gray badge */}
                        <TableCell className="text-xs text-slate-500 font-mono">
                          {cat.slug || "-"}
                        </TableCell>

                        {/* Column Mô tả */}
                        <TableCell className="max-w-xs truncate text-xs text-slate-500" title={cat.description || ""}>
                          {cat.description || "-"}
                        </TableCell>

                        {/* Column Ngày tạo */}
                        <TableCell className="text-xs text-slate-500">
                          {cat.created_at ? new Date(cat.created_at).toLocaleDateString("vi-VN") : "-"}
                        </TableCell>

                        {/* Column Thao tác */}
                        <TableCell className="text-right pr-5">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => handleOpenEdit(cat)}
                              className="h-7 w-7 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                              title="Chỉnh sửa danh mục"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-sm"
                              onClick={() => setDeleteTarget(cat)}
                              className="h-7 w-7 rounded-lg text-rose-500 hover:bg-rose-50 hover:text-rose-600"
                              title="Xóa danh mục"
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

      {/* Modal: Thêm danh mục */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="sm:max-w-md rounded-2xl overflow-hidden">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg font-bold text-heading">
              Thêm danh mục mới
            </DialogTitle>
            <DialogDescription className="sr-only">
              Thêm danh mục mới để phân loại tài liệu
            </DialogDescription>
          </DialogHeader>

          <form id="create-category-form" onSubmit={handleCreateCategory} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="create-name" className="text-xs font-semibold text-slate-700">
                Tên danh mục <span className="text-destructive">*</span>
              </Label>
              <Input
                id="create-name"
                placeholder="VD: Quy định Nghiên cứu Khoa học"
                value={createName}
                onChange={(e) => setCreateName(e.target.value)}
                disabled={isCreating}
                className="h-8 text-xs rounded-lg"
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="create-slug" className="text-xs font-semibold text-slate-700">
                Đường dẫn
              </Label>
              <Input
                id="create-slug"
                placeholder="VD: quy-dinh-nckh (Tùy chọn)"
                value={createSlug}
                onChange={(e) => setCreateSlug(e.target.value)}
                disabled={isCreating}
                className="h-8 text-xs rounded-lg font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="create-desc" className="text-xs font-semibold text-slate-700">
                Mô tả danh mục
              </Label>
              <Textarea
                id="create-desc"
                placeholder="Mô tả phạm vi hoặc đối tượng tài liệu của danh mục..."
                value={createDescription}
                onChange={(e) => setCreateDescription(e.target.value)}
                disabled={isCreating}
                rows={3}
                className="text-xs rounded-lg resize-none"
              />
            </div>
          </form>

          <DialogFooter className="mt-2 gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isCreating}
              onClick={() => setIsCreateOpen(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              form="create-category-form"
              size="sm"
              loading={isCreating}
              loadingText="Đang lưu..."
              disabled={!createName.trim()}
            >
              Lưu
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Chỉnh sửa danh mục */}
      <Dialog open={!!editTarget} onOpenChange={(open) => !open && setEditTarget(null)}>
        <DialogContent className="sm:max-w-md rounded-2xl overflow-hidden">
          <DialogHeader>
            <DialogTitle className="font-heading text-lg font-bold text-heading">
              Chỉnh sửa danh mục
            </DialogTitle>
            <DialogDescription className="sr-only">
              Chỉnh sửa thông tin danh mục
            </DialogDescription>
          </DialogHeader>

          <form id="edit-category-form" onSubmit={handleUpdateCategory} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="edit-name" className="text-xs font-semibold text-slate-700">
                Tên danh mục <span className="text-destructive">*</span>
              </Label>
              <Input
                id="edit-name"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                disabled={isUpdating}
                className="h-8 text-xs rounded-lg"
                autoFocus
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="edit-slug" className="text-xs font-semibold text-slate-700">
                Đường dẫn
              </Label>
              <Input
                id="edit-slug"
                value={editSlug}
                onChange={(e) => setEditSlug(e.target.value)}
                disabled={isUpdating}
                className="h-8 text-xs rounded-lg font-mono"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="edit-desc" className="text-xs font-semibold text-slate-700">
                Mô tả danh mục
              </Label>
              <Textarea
                id="edit-desc"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                disabled={isUpdating}
                rows={3}
                className="text-xs rounded-lg resize-none"
              />
            </div>
          </form>

          <DialogFooter className="mt-2 gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={isUpdating}
              onClick={() => setEditTarget(null)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              form="edit-category-form"
              size="sm"
              loading={isUpdating}
              loadingText="Đang lưu..."
              disabled={!editName.trim()}
            >
              Lưu
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Xác nhận xóa danh mục (Đồng bộ chuẩn modal xóa tài liệu) */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-rose-600" />
              <DialogTitle className="font-heading text-lg font-bold text-heading">
                Xóa danh mục
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted pt-1">
              Danh mục{" "}
              <strong className="text-heading font-semibold">&ldquo;{deleteTarget?.name}&rdquo;</strong> và toàn bộ
              dữ liệu liên quan sẽ bị xóa vĩnh viễn.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="gap-2 sm:gap-2 mt-4">
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
              onClick={handleDeleteCategory}
              loading={isDeleting}
              loadingText="Đang xóa..."
            >
              Xác nhận
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
