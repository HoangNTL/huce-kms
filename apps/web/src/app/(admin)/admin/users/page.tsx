"use client"

import * as React from "react"
import { Search, UserCheck, UserX, RotateCcw } from "lucide-react"
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
import type { UserProfile } from "@/types/user"

const sampleUsers: UserProfile[] = [
  {
    id: "usr-01",
    username: "admin_huce",
    email: "admin@huce.edu.vn",
    fullName: "Quản trị viên Hệ thống",
    role: "ADMIN",
    isActive: true,
    createdAt: "2024-01-15",
  },
  {
    id: "usr-02",
    username: "nguyenvana",
    email: "0123456@huce.edu.vn",
    fullName: "Nguyễn Văn A",
    role: "USER",
    isActive: true,
    createdAt: "2024-02-10",
  },
  {
    id: "usr-03",
    username: "tranthib",
    email: "0123457@huce.edu.vn",
    fullName: "Trần Thị B",
    role: "USER",
    isActive: false,
    createdAt: "2024-03-01",
  },
]

export default function AdminUsersPage() {
  const [users, setUsers] = React.useState<UserProfile[]>(sampleUsers)
  const [searchTerm, setSearchTerm] = React.useState("")
  const [roleFilter, setRoleFilter] = React.useState<string>("ALL")
  const [statusFilter, setStatusFilter] = React.useState<string>("ALL")
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(5)

  const handleToggleStatus = (id: string, current: boolean) => {
    setUsers((prev) => prev.map((u) => (u.id === id ? { ...u, isActive: !current } : u)))
    toast.success(current ? "Đã khóa tài khoản thành công" : "Đã kích hoạt lại tài khoản")
  }

  const filteredUsers = React.useMemo(() => {
    return users.filter((u) => {
      const matchSearch =
        u.fullName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.username.toLowerCase().includes(searchTerm.toLowerCase())

      const matchRole = roleFilter === "ALL" || u.role === roleFilter
      const matchStatus =
        statusFilter === "ALL" ||
        (statusFilter === "ACTIVE" && u.isActive) ||
        (statusFilter === "LOCKED" && !u.isActive)

      return matchSearch && matchRole && matchStatus
    })
  }, [users, searchTerm, roleFilter, statusFilter])

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / pageSize))
  const validPage = Math.min(currentPage, totalPages)

  // Paginated slice
  const paginatedUsers = React.useMemo(() => {
    const start = (validPage - 1) * pageSize
    return filteredUsers.slice(start, start + pageSize)
  }, [filteredUsers, validPage, pageSize])

  const hasActiveFilters = searchTerm !== "" || roleFilter !== "ALL" || statusFilter !== "ALL"

  return (
    <div className="space-y-6">
      {/* Page Title & Context in Content Canvas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="font-heading text-xl font-bold text-heading">Quản lý Tài khoản</h2>
          <p className="text-xs text-muted">
            Danh sách người dùng, sinh viên và phân quyền vai trò trong hệ thống
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
                value={roleFilter}
                onValueChange={(val) => {
                  setRoleFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả vai trò" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">Tất cả vai trò</SelectItem>
                  <SelectItem value="ADMIN">Quản trị viên (ADMIN)</SelectItem>
                  <SelectItem value="USER">Người dùng / SV (USER)</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={statusFilter}
                onValueChange={(val) => {
                  setStatusFilter(val ?? "ALL")
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="h-8 min-w-36 text-xs">
                  <SelectValue placeholder="Tất cả trạng thái" />
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
              {paginatedUsers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center text-xs text-muted">
                    Không tìm thấy tài khoản nào phù hợp với bộ lọc hiện tại.
                  </TableCell>
                </TableRow>
              ) : (
                paginatedUsers.map((user, idx) => {
                  const stt = (currentPage - 1) * pageSize + idx + 1
                  return (
                    <TableRow key={user.id}>
                      <TableCell className="w-14 text-center font-medium text-muted">
                        {stt}
                      </TableCell>
                      <TableCell className="text-xs font-medium text-heading">
                        {user.fullName}
                      </TableCell>
                      <TableCell className="text-xs text-muted">{user.username}</TableCell>
                      <TableCell className="text-xs text-muted">{user.email}</TableCell>
                      <TableCell>
                        <Badge
                          variant={user.role === "ADMIN" ? "default" : "outline"}
                          className="text-[10px]"
                        >
                          {user.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={user.isActive ? "default" : "destructive"}
                          className={`text-[10px] ${
                            user.isActive
                              ? "border-success/30 bg-success/15 text-success"
                              : "border-destructive/30 bg-destructive/15 text-destructive"
                          }`}
                        >
                          {user.isActive ? "Đang hoạt động" : "Đã khóa"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleToggleStatus(user.id, user.isActive)}
                          className="h-7 text-xs"
                        >
                          {user.isActive ? (
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
            currentPage={validPage}
            pageSize={pageSize}
            totalItems={filteredUsers.length}
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
