"use client"

import * as React from "react"
import { Search, UserCheck, UserX, RotateCcw, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardHeader, CardContent } from "@/components/ui/card"
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
import { DataTablePagination } from "@/components/shared/data-table-pagination"
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

  const handleToggleStatus = async (id: string | number, currentActive: boolean) => {
    try {
      await userService.updateStatus(id, { is_active: !currentActive })
      toast.success(!currentActive ? "Đã kích hoạt lại tài khoản thành công" : "Đã khóa tài khoản thành công")
      setRefreshKey((k) => k + 1)
    } catch (err) {
      toast.error("Cập nhật trạng thái tài khoản thất bại", {
        description: err instanceof Error ? err.message : "Lỗi kết nối máy chủ.",
      })
    }
  }

  const hasActiveFilters = searchTerm !== "" || roleFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title & Context in Content Canvas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">Quản lý Tài khoản</h2>
          <p className="text-xs text-muted">
            Danh sách tài khoản người dùng và phân quyền vai trò trong hệ thống ({totalItems} tài khoản)
          </p>
        </div>
      </div>

      <Card className="border-border shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Search Input with perfect vertical centering */}
            <div className="relative w-full sm:w-80">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
              <Input
                placeholder="Tìm theo tên, email, username..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1)
                }}
                className="pl-9 text-xs"
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
                <SelectTrigger className="h-8 min-w-36 text-xs">
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
                <SelectTrigger className="h-8 min-w-36 text-xs">
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
                  className="h-8 gap-1 text-xs text-muted hover:text-heading"
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Đặt lại</span>
                </Button>
              )}
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-14 text-center">STT</TableHead>
                <TableHead>Họ và tên</TableHead>
                <TableHead>Tên đăng nhập</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Vai trò</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead className="text-right">Thao tác</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-brand-primary" />
                      <span>Đang tải danh sách tài khoản từ máy chủ...</span>
                    </div>
                  </TableCell>
                </TableRow>
              ) : users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    Không tìm thấy tài khoản nào phù hợp với bộ lọc hiện tại.
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user, idx) => {
                  const stt = (currentPage - 1) * pageSize + idx + 1
                  const roleStr = String(user.role || "").toUpperCase()
                  const isActiveBool = user.is_active ?? true

                  return (
                    <TableRow key={String(user.id)}>
                      <TableCell className="w-14 text-center font-medium text-muted">
                        {stt}
                      </TableCell>
                      <TableCell className="text-xs font-medium text-heading">
                        {user.full_name || user.username}
                      </TableCell>
                      <TableCell className="text-xs text-muted">{user.username}</TableCell>
                      <TableCell className="text-xs text-muted">{user.email}</TableCell>
                      <TableCell>
                        <Badge
                          variant={roleStr === "ADMIN" ? "default" : "outline"}
                          className="text-[10px]"
                        >
                          {roleStr}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={isActiveBool ? "default" : "destructive"}
                          className={`text-[10px] ${
                            isActiveBool
                              ? "border-success/30 bg-success/15 text-success"
                              : "border-destructive/30 bg-destructive/15 text-destructive"
                          }`}
                        >
                          {isActiveBool ? "Đang hoạt động" : "Đã khóa"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleStatus(user.id, isActiveBool)}
                          className="h-7 text-xs"
                        >
                          {isActiveBool ? (
                            <span className="flex items-center gap-1 text-destructive">
                              <UserX className="h-3.5 w-3.5" /> Khóa
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-success">
                              <UserCheck className="h-3.5 w-3.5" /> Mở khóa
                            </span>
                          )}
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>

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
    </div>
  )
}
