"use client"

import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/components/ui/sonner"
import { documentService } from "../services/document-service"
import type { DocumentMetadata } from "../types"
import type { CategoryItem } from "@/features/categories"

interface DocumentEditModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  document:
    | DocumentMetadata
    | {
        id: string | number
        title: string
        category_id?: string | null
        category?: { id?: string | number; name?: string } | string
      }
    | null
  categories?: CategoryItem[]
  onSuccess?: () => void
}

interface DocumentEditFormContentProps {
  document: NonNullable<DocumentEditModalProps["document"]>
  categories: CategoryItem[]
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

function DocumentEditFormContent({
  document,
  categories,
  onOpenChange,
  onSuccess,
}: DocumentEditFormContentProps) {
  const initialTitle = document.title || ""
  const initialCategory = React.useMemo(() => {
    if (document.category_id) return String(document.category_id)
    if (typeof document.category === "object" && document.category?.id) {
      return String(document.category.id)
    }
    return ""
  }, [document])

  const [title, setTitle] = React.useState(initialTitle)
  const [selectedCategoryId, setSelectedCategoryId] = React.useState<string>(initialCategory)
  const [isLoading, setIsLoading] = React.useState(false)

  const categoryOptions: Record<string, string> = React.useMemo(() => {
    const map: Record<string, string> = {}
    for (const cat of categories) {
      map[String(cat.id)] = cat.name
    }
    return map
  }, [categories])

  const handleSave = async (e?: React.SubmitEvent<HTMLFormElement>) => {
    if (e) e.preventDefault()

    const cleanTitle = title.trim()
    if (!cleanTitle || cleanTitle.length < 2) {
      toast.error("Tiêu đề không hợp lệ", {
        description: "Tiêu đề tài liệu phải có ít nhất 2 ký tự.",
      })
      return
    }

    try {
      setIsLoading(true)
      await documentService.updateDocument(document.id, {
        title: cleanTitle,
        category_id: selectedCategoryId || null,
      })
      toast.success("Cập nhật tài liệu thành công!", {
        description: `Tài liệu "${cleanTitle}" đã được cập nhật thông tin.`,
      })
      onOpenChange(false)
      onSuccess?.()
    } catch (err) {
      toast.error("Cập nhật thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <form id="edit-doc-form" onSubmit={handleSave} className="space-y-4 py-2 min-w-0">
        {/* Tên tài liệu */}
        <div className="space-y-1.5 min-w-0">
          <Label htmlFor="doc-title" className="text-xs shrink-0">
            Tên tài liệu
          </Label>
          <Input
            id="doc-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Nhập tên tài liệu..."
            required
            minLength={2}
            maxLength={255}
            disabled={isLoading}
            className="w-full min-w-0 rounded-lg text-xs"
          />
        </div>

        {/* Danh mục */}
        <div className="space-y-1.5 min-w-0">
          <Label htmlFor="doc-category" className="text-xs shrink-0">
            Danh mục tài liệu
          </Label>
          <Select
            items={categoryOptions}
            value={selectedCategoryId}
            onValueChange={(val) => setSelectedCategoryId(val || "")}
            disabled={isLoading}
          >
            <SelectTrigger id="doc-category" className="w-full rounded-lg text-xs">
              <SelectValue placeholder="Chọn danh mục">
                {(val) => categoryOptions[String(val)] || "Chọn danh mục"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {categories.length > 0 ? (
                categories.map((cat) => (
                  <SelectItem key={String(cat.id)} value={String(cat.id)}>
                    {cat.name}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="" disabled>
                  Chưa có danh mục nào
                </SelectItem>
              )}
            </SelectContent>
          </Select>
        </div>
      </form>

      <DialogFooter className="mt-2 gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isLoading}
          onClick={() => onOpenChange(false)}
        >
          Hủy
        </Button>
        <Button
          type="submit"
          form="edit-doc-form"
          size="sm"
          loading={isLoading}
          loadingText="Đang lưu..."
          disabled={!title.trim()}
        >
          Lưu
        </Button>
      </DialogFooter>
    </>
  )
}

export function DocumentEditModal({
  open,
  onOpenChange,
  document,
  categories = [],
  onSuccess,
}: DocumentEditModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg rounded-2xl overflow-hidden">
        <DialogHeader>
          <DialogTitle className="font-heading text-lg font-bold text-heading">
            Chỉnh sửa tài liệu
          </DialogTitle>
          <DialogDescription className="sr-only">
            Cập nhật tên và danh mục cho tài liệu trong cơ sở tri thức
          </DialogDescription>
        </DialogHeader>

        {open && document && (
          <DocumentEditFormContent
            key={String(document.id)}
            document={document}
            categories={categories}
            onOpenChange={onOpenChange}
            onSuccess={onSuccess}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}
