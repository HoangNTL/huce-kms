import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { DocumentStatus } from "../types"

interface DocumentStatusBadgeProps {
  status: DocumentStatus | number
}

export const DOCUMENT_STATUS_CONFIG: Record<
  DocumentStatus,
  { label: string; variant: "default" | "secondary" | "outline" | "destructive"; className: string }
> = {
  [DocumentStatus.UPLOADED]: {
    label: "Đã tải lên",
    variant: "outline",
    className: "text-muted",
  },
  [DocumentStatus.PENDING]: {
    label: "Chờ xử lý",
    variant: "outline",
    className: "text-muted",
  },
  [DocumentStatus.PROCESSING]: {
    label: "Đang xử lý",
    variant: "secondary",
    className: "animate-pulse border-warning/30 bg-warning/15 text-warning",
  },
  [DocumentStatus.INDEXED]: {
    label: "Đã lập chỉ mục",
    variant: "default",
    className: "border-success/30 bg-success/15 text-success",
  },
  [DocumentStatus.FAILED]: {
    label: "Thất bại",
    variant: "destructive",
    className: "border-destructive/30 bg-destructive/15 text-destructive",
  },
}

export function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const config = DOCUMENT_STATUS_CONFIG[status as DocumentStatus] ?? DOCUMENT_STATUS_CONFIG[DocumentStatus.UPLOADED]

  return (
    <Badge variant={config.variant} className={config.className}>
      {config.label}
    </Badge>
  )
}
