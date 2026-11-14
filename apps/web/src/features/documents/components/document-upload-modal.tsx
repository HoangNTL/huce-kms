"use client"

import * as React from "react"
import { UploadCloud, FileText, X } from "lucide-react"
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
import type { CategoryItem } from "../types"

interface DocumentUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function DocumentUploadModal({ open, onOpenChange, onSuccess }: DocumentUploadModalProps) {
  const [file, setFile] = React.useState<File | null>(null)
  const [title, setTitle] = React.useState("")
  const [categories, setCategories] = React.useState<CategoryItem[]>([])
  const [selectedCategoryId, setSelectedCategoryId] = React.useState<string>("")
  const [isLoading, setIsLoading] = React.useState(false)

  const categoryOptions: Record<string, string> = React.useMemo(() => {
    const map: Record<string, string> = {
      "1": "Quy chế Đào tạo",
      "2": "Quy chế Sinh viên",
      "3": "Học bổng, học phí",
      "4": "Biểu mẫu Hành chính",
    }
    for (const cat of categories) {
      map[String(cat.id)] = cat.name
    }
    return map
  }, [categories])

  React.useEffect(() => {
    if (open) {
      documentService
        .getCategories()
        .then((cats) => {
          setCategories(cats || [])
          if (cats && cats.length > 0 && !selectedCategoryId) {
            setSelectedCategoryId(String(cats[0].id))
          }
        })
        .catch(() => {
          // If category endpoint fails, fallback to empty
        })
    }
  }, [open, selectedCategoryId])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      if (!title) {
        const defaultTitle = selectedFile.name.replace(/\.[^/.]+$/, "")
        setTitle(defaultTitle)
      }
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error("Vui lòng chọn tệp tin cần tải lên")
      return
    }

    setIsLoading(true)
    try {
      const doc = await documentService.uploadDocument(
        file,
        title || undefined,
        selectedCategoryId ? Number(selectedCategoryId) : undefined
      )

      toast.success("Tải lên tài liệu thành công!", {
        description: `Tài liệu "${doc.title || file.name}" đã được nạp và phân mảnh vào hệ thống RAG.`,
      })
      setFile(null)
      setTitle("")
      onOpenChange(false)
      if (onSuccess) onSuccess()
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : "Tải tài liệu lên thất bại. Vui lòng thử lại."
      toast.error("Tải tài liệu lên thất bại", {
        description: errorMsg,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md rounded-2xl">
        <DialogHeader>
          <DialogTitle className="font-heading text-lg font-bold text-heading">
            Tải lên tài liệu
          </DialogTitle>
          <DialogDescription className="sr-only">
            Tải lên tài liệu vào cơ sở tri thức hệ thống
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="doc-title" className="text-xs">Tên tài liệu</Label>
            <Input
              id="doc-title"
              placeholder="Nhập tên tài liệu..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isLoading}
              className="rounded-xl text-xs"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="category">Danh mục tài liệu</Label>
            <Select
              items={categoryOptions}
              value={selectedCategoryId}
              onValueChange={(val) => setSelectedCategoryId(val || "")}
            >
              <SelectTrigger id="category" className="w-full">
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
                  <>
                    <SelectItem value="1">Quy chế Đào tạo</SelectItem>
                    <SelectItem value="2">Quy chế Sinh viên</SelectItem>
                    <SelectItem value="3">Học bổng, học phí</SelectItem>
                    <SelectItem value="4">Biểu mẫu Hành chính</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Tệp tin tài liệu</Label>
            <div className="relative flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface/50 p-6 text-center transition-colors hover:bg-surface">
              <input
                type="file"
                accept=".pdf,.txt,.md"
                onChange={handleFileChange}
                disabled={isLoading}
                className="absolute inset-0 cursor-pointer opacity-0"
              />
              <UploadCloud className="mb-2 h-8 w-8 text-brand-primary" />
              <p className="text-xs font-semibold text-heading">Kéo thả hoặc nhấp để chọn tệp</p>
              <p className="mt-1 text-[11px] text-muted">
                Định dạng hỗ trợ: PDF, TXT, MD (Tối đa 25MB)
              </p>
            </div>
            {file && (
              <div className="mt-2 flex items-center justify-between rounded-lg border border-border bg-surface p-2.5 text-xs text-heading">
                <div className="flex items-center gap-2 truncate">
                  <FileText className="h-4 w-4 shrink-0 text-brand-primary" />
                  <span className="truncate font-medium">{file.name}</span>
                  <span className="text-[11px] text-muted">
                    ({(file.size / 1024 / 1024).toFixed(2)} MB)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  disabled={isLoading}
                  className="text-muted hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="mt-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
            className="rounded-xl text-xs"
          >
            Hủy
          </Button>
          <Button
            size="sm"
            onClick={handleUpload}
            disabled={!file || isLoading}
            className="rounded-xl bg-brand-primary text-xs font-medium text-white shadow-xs hover:bg-brand-primary-hover"
          >
            {isLoading ? "Đang tải lên..." : "Tải lên"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
