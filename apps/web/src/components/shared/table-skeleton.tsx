import * as React from "react"
import { TableRow, TableCell } from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export interface TableSkeletonProps {
  columns: number
  rows?: number
  className?: string
}

export function TableSkeleton({ columns, rows = 5, className }: TableSkeletonProps) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rIdx) => (
        <TableRow key={rIdx} className={cn("hover:bg-transparent", className)}>
          {Array.from({ length: columns }).map((_, cIdx) => (
            <TableCell key={cIdx} className="py-3.5">
              <Skeleton
                className={cn(
                  "h-4",
                  cIdx === 0
                    ? "mx-auto h-4 w-6"
                    : cIdx === 1
                      ? "h-4 w-4/5 max-w-[280px]"
                      : cIdx === columns - 1
                        ? "ml-auto h-4 w-16"
                        : "h-4 w-1/2 max-w-[120px]"
                )}
              />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  )
}
