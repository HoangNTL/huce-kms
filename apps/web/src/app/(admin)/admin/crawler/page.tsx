"use client"

import * as React from "react"
import { Globe, Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { toast } from "@/components/ui/sonner"
import type { CrawlSource } from "@/features/crawler"

const sampleSources: CrawlSource[] = [
  {
    id: "src-01",
    name: "Cổng Thông tin Đào tạo HUCE",
    url: "https://daotao.huce.edu.vn",
    crawlDepth: 2,
    scheduleCron: "0 2 * * *",
    isActive: true,
    lastCrawledAt: "2024-03-14 02:00",
    createdAt: "2024-01-01",
  },
  {
    id: "src-02",
    name: "Phòng Công tác Chính trị & Sinh viên",
    url: "https://ctsv.huce.edu.vn",
    crawlDepth: 2,
    scheduleCron: "0 4 * * 1",
    isActive: true,
    lastCrawledAt: "2024-03-11 04:00",
    createdAt: "2024-01-05",
  },
]

export default function AdminCrawlerPage() {
  const [sources] = React.useState<CrawlSource[]>(sampleSources)

  const handleTrigger = (name: string) => {
    toast.success("Bắt đầu tác vụ cào dữ liệu!", {
      description: `Đang quét và thu thập tài liệu mới từ "${name}"...`,
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">
            Nguồn Dữ liệu & Tác vụ Crawl
          </h2>
          <p className="text-xs text-muted">
            Quản trị các URL nguồn thu thập thông tin tự động từ website Trường Đại học Xây dựng Hà
            Nội
          </p>
        </div>
      </div>

      <Card className="border-border shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="h-4 w-4 text-brand-primary" />
              <CardTitle className="font-heading text-sm font-bold text-heading">
                Danh sách Nguồn Web Thu thập
              </CardTitle>
            </div>
            <p className="text-xs text-muted">{sources.length} nguồn đang hoạt động</p>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14 text-center">STT</TableHead>
                <TableHead>Tên nguồn</TableHead>
                <TableHead>Địa chỉ URL</TableHead>
                <TableHead>Độ sâu</TableHead>
                <TableHead>Lần cào gần nhất</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead className="text-right">Kích hoạt</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sources.map((src, idx) => (
                <TableRow key={src.id}>
                  <TableCell className="w-14 text-center font-medium text-muted">
                    {idx + 1}
                  </TableCell>
                  <TableCell className="text-xs font-medium text-heading">{src.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted">{src.url}</TableCell>
                  <TableCell className="text-xs text-muted">{src.crawlDepth} cấp</TableCell>
                  <TableCell className="text-xs text-muted">
                    {src.lastCrawledAt || "Chưa cào"}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="default"
                      className="border-success/30 bg-success/15 text-[10px] text-success"
                    >
                      Hoạt động
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTrigger(src.name)}
                      className="h-7 gap-1 text-xs"
                    >
                      <Play className="h-3 w-3 text-brand-primary" />
                      <span>Cào ngay</span>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
