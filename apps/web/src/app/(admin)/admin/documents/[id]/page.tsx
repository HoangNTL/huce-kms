"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowLeft, Save, Layers } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { DocumentStatusBadge, type DocumentChunk } from "@/features/documents"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

interface DocumentDetailPageProps {
  params: Promise<{ id: string }>
}

const sampleChunks: DocumentChunk[] = [
  {
    id: "chk-01",
    documentId: "doc-01",
    chunkIndex: 0,
    content:
      "Chương I: QUY ĐỊNH CHUNG. Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng. Quy chế này quy định về tổ chức và quản lý đào tạo trình độ đại học theo hệ thống tín chỉ đối với các hình thức đào tạo chính quy tại Trường Đại học Xây dựng Hà Nội...",
    tokenCount: 185,
  },
  {
    id: "chk-02",
    documentId: "doc-01",
    chunkIndex: 1,
    content:
      "Điều 2. Thời gian và kế hoạch đào tạo. Trường tổ chức đào tạo theo các khóa học, năm học và học kỳ. Một năm học có hai học kỳ chính và một học kỳ phụ. Thời gian tối đa để hoàn thành chương trình không vượt quá 2 lần thời gian thiết kế của khóa học...",
    tokenCount: 210,
  },
]

export default function DocumentDetailPage({ params }: DocumentDetailPageProps) {
  const resolvedParams = React.use(params)
  const [title, setTitle] = React.useState("Quy chế đào tạo trình độ đại học chính quy 2024")
  const [category, setCategory] = React.useState("Quy chế")
  const [isLoading, setIsLoading] = React.useState(false)

  const handleSave = async (e: React.SubmitEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      await new Promise((res) => setTimeout(res, 600))
      toast.success("Cập nhật thông tin tài liệu thành công!")
    } catch {
      toast.error("Cập nhật thất bại")
    } finally {
      setIsLoading(false)
    }
  }

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
          <p className="text-xs text-muted">Mã tài liệu: {resolvedParams.id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Metadata Edit Form */}
        <Card className="h-fit border-border shadow-xs lg:col-span-1">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Thông tin Tài liệu
              </CardTitle>
              <DocumentStatusBadge status="INDEXED" />
            </div>
            <CardDescription className="text-xs">
              Chỉnh sửa metadata phục vụ tìm kiếm
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSave}>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="title" className="text-xs">
                  Tên văn bản
                </Label>
                <Input
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="category" className="text-xs">
                  Danh mục
                </Label>
                <Input
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="text-xs"
                />
              </div>

              <div className="space-y-2 rounded-lg border border-border bg-surface/50 p-3 text-[11px] text-muted">
                <div className="flex justify-between">
                  <span>Tên tệp gốc:</span>
                  <span className="font-medium text-heading">quy_che_2024.pdf</span>
                </div>
                <div className="flex justify-between">
                  <span>Kích thước:</span>
                  <span className="font-medium text-heading">2.34 MB</span>
                </div>
                <div className="flex justify-between">
                  <span>Tổng chunks:</span>
                  <span className="font-medium font-semibold text-brand-primary">148 chunks</span>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full gap-1.5 bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
              >
                <Save className="h-3.5 w-3.5" />
                {isLoading ? "Đang lưu..." : "Lưu thay đổi"}
              </Button>
            </CardContent>
          </form>
        </Card>

        {/* Chunks Explorer */}
        <Card className="border-border shadow-xs lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-brand-primary" />
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Danh sách Chunks Trích xuất (Vector Chunks)
              </CardTitle>
            </div>
            <CardDescription className="text-xs">
              Các đoạn văn bản đã bóc tách được embedding và đối chiếu khi người dùng tra cứu AI
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {sampleChunks.map((chk) => (
              <div
                key={chk.id}
                className="space-y-2 rounded-lg border border-border bg-surface/50 p-4 text-xs"
              >
                <div className="flex items-center justify-between text-[11px] font-semibold text-muted">
                  <span className="text-brand-primary">
                    Chunk #{chk.chunkIndex + 1} ({chk.id})
                  </span>
                  <span>{chk.tokenCount} tokens</span>
                </div>
                <p className="leading-relaxed text-body">{chk.content}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
