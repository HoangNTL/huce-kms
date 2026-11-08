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
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "@/components/ui/sonner"

interface DocumentUploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

export function DocumentUploadModal({ open, onOpenChange, onSuccess }: DocumentUploadModalProps) {
  const [file, setFile] = React.useState<File | null>(null)
  const [category, setCategory] = React.useState("Quy chế")
  const [isLoading, setIsLoading] = React.useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) {
      toast.error("Vui lòng chọn tệp tin cần tải lên")
      return
    }

    setIsLoading(true)
    try {
      await new Promise((res) => setTimeout(res, 1000))
      toast.success("Tải lên tài liệu thành công!", {
        description: `Tài liệu "${file.name}" đã được đưa vào hàng đợi bóc tách chunks & index vector.`,
      })
      setFile(null)
      onOpenChange(false)
      if (onSuccess) onSuccess()
    } catch {
      toast.error("Tải tài liệu lên thất bại")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base text-brand-primary">
            <UploadCloud className="h-5 w-5" />
            <span>Tải lên Tài liệu Tri thức Mới</span>
          </DialogTitle>
          <DialogDescription>
            Hệ thống hỗ trợ các định dạng .PDF, .DOCX. Sau khi tải lên, tài liệu sẽ tự động được
            phân mảnh và nạp vào vector database.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="category">Danh mục tài liệu</Label>
            <Select value={category} onValueChange={(val) => setCategory(val || "Quy chế")}>
              <SelectTrigger id="category" className="w-full">
                <SelectValue placeholder="Chọn danh mục" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Quy chế">Quy chế Đào tạo</SelectItem>
                <SelectItem value="Quy định">Quy định Học bổng & Học phí</SelectItem>
                <SelectItem value="Hướng dẫn">Hướng dẫn Đồ án Tốt nghiệp</SelectItem>
                <SelectItem value="Biểu mẫu">Biểu mẫu & Thủ tục Hành chính</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>Tệp tin tài liệu</Label>
            <div className="relative flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-border bg-surface/50 p-6 text-center transition-colors hover:bg-surface">
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={handleFileChange}
                className="absolute inset-0 cursor-pointer opacity-0"
              />
              <UploadCloud className="mb-2 h-8 w-8 text-brand-primary" />
              <p className="text-xs font-semibold text-heading">Kéo thả hoặc nhấp để chọn tệp</p>
              <p className="mt-1 text-[11px] text-muted">
                Định dạng hỗ trợ: PDF, DOCX (Tối đa 25MB)
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
                  className="text-muted hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="mt-2 gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Hủy
          </Button>
          <Button
            onClick={handleUpload}
            disabled={!file || isLoading}
            className="bg-brand-primary text-white hover:bg-brand-primary-hover"
          >
            {isLoading ? "Đang tải lên..." : "Tải lên & Xử lý"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
