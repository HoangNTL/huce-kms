import * as React from "react"
import { Badge } from "@/components/ui/badge"
import type { DocumentStatus } from "../types"

interface DocumentStatusBadgeProps {
  status: DocumentStatus
}

export function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const norm = (status || "").toUpperCase()
  switch (norm) {
    case "INDEXED":
      return (
        <Badge variant="default" className="border-success/30 bg-success/15 text-success">
          Đã lập chỉ mục
        </Badge>
      )
    case "PROCESSING":
      return (
        <Badge
          variant="secondary"
          className="animate-pulse border-warning/30 bg-warning/15 text-warning"
        >
          Đang xử lý
        </Badge>
      )
    case "UPLOADED":
    case "PENDING":
      return (
        <Badge variant="outline" className="text-muted">
          Đã tải lên
        </Badge>
      )
    case "FAILED":
      return (
        <Badge
          variant="destructive"
          className="border-destructive/30 bg-destructive/15 text-destructive"
        >
          Thất bại
        </Badge>
      )
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}
