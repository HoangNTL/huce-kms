"use client"

import * as React from "react"
import {
  Search,
  RotateCcw,
  Lock,
  Unlock,
  ShieldCheck,
  User as UserIcon,
  AlertCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { DataTablePagination } from "@/components/shared/data-table-pagination"
import { TableSkeleton } from "@/components/shared/table-skeleton"
import { toast } from "@/components/ui/sonner"
import { userService } from "@/features/users/services/user-service"
import { USER_ROLES, ROLE_LABELS, type UserProfile, type UserRole } from "@/types/user"

const ROLE_OPTIONS: Record<string, string> = {
  ALL: "Tất cả vai trò",
  ADMIN: ROLE_LABELS[USER_ROLES.ADMIN],
  USER: ROLE_LABELS[USER_ROLES.USER],
}

const STATUS_OPTIONS: Record<string, string> = {
  ALL: "Tất cả trạng thái",
  ACTIVE: "Đang hoạt động",
  LOCKED: "Đã khóa",
}

export default function AdminUsersPage() {
  const [users, setUsers] = React.useState<UserProfile[]>([])
  const [isLoading, setIsLoading] = React.useState(true)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [roleFilter, setRoleFilter] = React.useState<string>("ALL")
  const [statusFilter, setStatusFilter] = React.useState<string>("ALL")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(10)
  const [totalItems, setTotalItems] = React.useState(0)
  const [refreshKey, setRefreshKey] = React.useState(0)

  // Dialog States
  const [toggleTarget, setToggleTarget] = React.useState<UserProfile | null>(null)
  const [isUpdatingStatus, setIsUpdatingStatus] = React.useState(false)

  React.useEffect(() => {
    let ignore = false
    userService
      .getUsers({
        page: currentPage,
        pageSize,
        search: searchTerm.trim() || undefined,
        role: roleFilter !== "ALL" ? roleFilter.toLowerCase() : undefined,
        is_active: statusFilter === "ACTIVE" ? true : statusFilter === "LOCKED" ? false : undefined,
      })
      .then((res) => {
        if (!ignore) {
          const mapped: UserProfile[] = (res.items || []).map((u) => ({
            ...u,
            id: String(u.id),
            full_name: u.full_name || u.username,
            role: (String(u.role || USER_ROLES.USER).toLowerCase() as UserRole),
            is_active: u.is_active ?? true,
          }))
          setUsers(mapped)
          setTotalItems(res.total ?? mapped.length)
          setIsLoading(false)
        }
      })
      .catch((err) => {
        if (!ignore) {
          toast.error("Không thể tải danh sách tài khoản", {
            description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
          })
          setIsLoading(false)
        }
      })
    return () => {
      ignore = true
    }
  }, [currentPage, pageSize, searchTerm, roleFilter, statusFilter, refreshKey])

  const handleConfirmToggleStatus = async () => {
    if (!toggleTarget) return
    setIsUpdatingStatus(true)
    const currentActive = toggleTarget.is_active ?? true
    try {
      await userService.updateStatus(toggleTarget.id, { is_active: !currentActive })
      toast.success(
        !currentActive
          ? `Đã mở khóa tài khoản "${toggleTarget.username}" thành công`
          : `Đã khóa tài khoản "${toggleTarget.username}" thành công`
      )
      setToggleTarget(null)
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Cập nhật trạng thái tài khoản thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    } finally {
      setIsUpdatingStatus(false)
    }
  }

  const hasActiveFilters = searchTerm !== "" || roleFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title: Clean & Focused */}
      <div>
        <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
          Quản lý Tài khoản
        </h1>
      </div>

      <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0">
        <div className="p-4 border-b border-border/50">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input with perfect vertical centering */}
            <div className="relative w-full sm:w-80">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Tìm theo họ tên, email, tên đăng nhập..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1)
                }}
                className="pl-9 text-xs rounded-lg"
              />
            </div>

            {/* Filter toolbar */}
            <div className="flex flex-wrap items-center gap-2">
              <Select
                items={ROLE_OPTIONS}
                value={roleFilter}
                onValueChange={(val) => {
                  setRoleFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 rounded-lg text-xs">
                  <SelectValue placeholder="Tất cả vai trò">
                    {(val) => ROLE_OPTIONS[String(val)] || "Tất cả vai trò"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả vai trò</SelectItem>
                  <SelectItem value="ADMIN">Quản trị viên</SelectItem>
                  <SelectItem value="USER">Người dùng</SelectItem>
                </SelectContent>
              </Select>

              <Select
                items={STATUS_OPTIONS}
                value={statusFilter}
                onValueChange={(val) => {
                  setStatusFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 rounded-lg text-xs">
                  <SelectValue placeholder="Tất cả trạng thái">
                    {(val) => STATUS_OPTIONS[String(val)] || "Tất cả trạng thái"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả trạng thái</SelectItem>
                  <SelectItem value="ACTIVE">Đang hoạt động</SelectItem>
                  <SelectItem value="LOCKED">Đã khóa</SelectItem>
                </SelectContent>
              </Select>

              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchTerm("")
                    setRoleFilter("ALL")
                    setStatusFilter("ALL")
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
                    Họ và tên
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Tên đăng nhập
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Email
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Vai trò
                  </TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Trạng thái
                  </TableHead>
                  <TableHead className="text-right text-[11px] font-semibold uppercase tracking-wider text-slate-400 pr-5">
                    Thao tác
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableSkeleton columns={7} rows={5} />
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-36 text-center text-xs text-muted">
                      Không tìm thấy tài khoản nào phù hợp với bộ lọc hiện tại.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user, idx) => {
                    const stt = (currentPage - 1) * pageSize + idx + 1
                    const isAdmin = String(user.role).toLowerCase() === USER_ROLES.ADMIN
                    const isActive = user.is_active ?? true
                    const fullName = user.full_name || user.username

                    return (
                      <TableRow
                        key={String(user.id)}
                        className="transition-colors hover:bg-slate-50/60"
                      >
                        {/* Column STT */}
                        <TableCell className="w-14 text-center text-xs font-medium text-slate-500">
                          {stt}
                        </TableCell>

                        {/* Column Họ và tên */}
                        <TableCell className="text-xs font-semibold text-slate-900">
                          {fullName}
                        </TableCell>

                        {/* Column Tên đăng nhập */}
                        <TableCell className="text-xs font-medium text-slate-600">
                          {user.username}
                        </TableCell>

                        {/* Column Email */}
                        <TableCell className="text-xs text-slate-500 font-normal">
                          {user.email}
                        </TableCell>

                        {/* Column Vai trò: Vietnamese Pill Badges with Pastel Colors */}
                        <TableCell>
                          {isAdmin ? (
                            <span className="inline-flex items-center gap-1 rounded-full border border-violet-200/80 bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-700 shadow-2xs">
                              <ShieldCheck className="h-3.5 w-3.5" />
                              Quản trị viên
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full border border-sky-200/80 bg-sky-50 px-2.5 py-0.5 text-xs font-medium text-sky-700 shadow-2xs">
                              <UserIcon className="h-3.5 w-3.5" />
                              Người dùng
                            </span>
                          )}
                        </TableCell>

                        {/* Column Trạng thái: Pill Badges with Pulse Indicator */}
                        <TableCell>
                          {isActive ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200/80 bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 shadow-2xs">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                              Đang hoạt động
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200/80 bg-rose-50 px-2.5 py-0.5 text-xs font-medium text-rose-700 shadow-2xs">
                              <span className="h-1.5 w-1.5 rounded-full bg-rose-500"></span>
                              Đã khóa
                            </span>
                          )}
                        </TableCell>

                        {/* Column Thao tác */}
                        <TableCell className="text-right pr-5">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => setToggleTarget(user)}
                            title={isActive ? "Khóa tài khoản" : "Mở khóa tài khoản"}
                            className={`h-7 w-7 rounded-lg transition-colors ${
                              isActive
                                ? "text-rose-500 hover:bg-rose-50 hover:text-rose-600"
                                : "text-emerald-600 hover:bg-emerald-50 hover:text-emerald-700"
                            }`}
                          >
                            {isActive ? (
                              <Lock className="h-3.5 w-3.5" />
                            ) : (
                              <Unlock className="h-3.5 w-3.5" />
                            )}
                          </Button>
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


      {/* Lock/Unlock Confirmation Dialog */}
      <Dialog open={!!toggleTarget} onOpenChange={(open) => !open && setToggleTarget(null)}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <AlertCircle
                className={`h-5 w-5 ${
                  toggleTarget?.is_active ? "text-rose-600" : "text-emerald-600"
                }`}
              />
              <DialogTitle className="font-heading text-lg font-bold text-heading">
                {toggleTarget?.is_active ? "Khóa tài khoản" : "Mở khóa tài khoản"}
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted pt-1">
              {toggleTarget?.is_active ? (
                <>
                  Tài khoản{" "}
                  <strong className="text-heading">&ldquo;{toggleTarget?.username}&rdquo;</strong> sẽ
                  không thể đăng nhập vào hệ thống.
                </>
              ) : (
                <>
                  Tài khoản{" "}
                  <strong className="text-heading">&ldquo;{toggleTarget?.username}&rdquo;</strong> sẽ
                  được phép đăng nhập trở lại.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setToggleTarget(null)}
              disabled={isUpdatingStatus}
              className="rounded-lg text-xs"
            >
              Hủy
            </Button>
            <Button
              size="sm"
              onClick={handleConfirmToggleStatus}
              loading={isUpdatingStatus}
              loadingText="Đang xử lý..."
              className={`rounded-lg text-xs font-medium text-white shadow-xs ${
                toggleTarget?.is_active
                  ? "bg-rose-600 hover:bg-rose-700"
                  : "bg-emerald-600 hover:bg-emerald-700"
              }`}
            >
              Xác nhận
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
