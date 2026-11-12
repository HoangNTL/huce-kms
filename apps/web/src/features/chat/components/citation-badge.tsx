"use client"

import * as React from "react"
import { BookOpen } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import type { Citation } from "../types"

interface CitationBadgeProps {
  citation: Citation
  index: number
}

export function CitationBadge({ citation, index }: CitationBadgeProps) {
  const [open, setOpen] = React.useState(false)

  const docTitle = citation.title || "Tài liệu HUCE"
  const page = citation.page_number
  const chunkIdentifier = citation.chunk_index !== undefined ? `#${citation.chunk_index}` : ""

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group mx-1 inline-flex cursor-pointer items-center gap-1 align-baseline"
        title={`Xem tài liệu nguồn: ${docTitle}`}
      >
        <Badge
          variant="outline"
          className="h-5 border-brand-primary/30 bg-brand-primary/5 px-1.5 text-[11px] font-normal text-brand-primary transition-colors group-hover:bg-brand-primary/10"
        >
          <BookOpen className="mr-0.5 h-3 w-3 text-brand-primary" />
          <span>[{index + 1}]</span>
        </Badge>
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base text-brand-primary">
              <BookOpen className="h-5 w-5" />
              <span>Tài liệu Đối chứng Nguồn</span>
            </DialogTitle>
            <DialogDescription className="pt-1 font-medium text-heading">
              {docTitle}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 pt-2">
            <div className="max-h-60 overflow-y-auto rounded-lg border border-border bg-surface/50 p-3.5 text-xs leading-relaxed text-body">
              <p className="mb-1 text-[11px] font-semibold tracking-wider text-brand-primary text-heading uppercase">
                Đoạn trích dẫn liên quan:
              </p>
              &ldquo;{citation.snippet}&rdquo;
            </div>

            <div className="flex items-center justify-between pt-1 text-xs text-muted">
              {chunkIdentifier && <span>Mã chunk: {chunkIdentifier}</span>}
              {page !== undefined && <span>Trang số: {page}</span>}
              {citation.score !== undefined && (
                <span className="font-medium text-emerald-600">
                  Độ khớp: {(citation.score * 100).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
