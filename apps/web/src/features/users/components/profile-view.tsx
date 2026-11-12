"use client"

import * as React from "react"
import { ShieldCheck, User, KeyRound, Check, LogOut } from "lucide-react"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { toast } from "@/components/ui/sonner"
import { useAuthStore } from "@/stores/use-auth-store"
import { userService } from "@/features/users/services/user-service"
import { USER_ROLES, ROLE_LABELS } from "@/types/user"

export function ProfileView() {
  const { user, fetchCurrentUser, logout } = useAuthStore()
  const [currentPassword, setCurrentPassword] = React.useState("")
  const [newPassword, setNewPassword] = React.useState("")
  const [confirmPassword, setConfirmPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)

  const isAdmin = user?.role === USER_ROLES.ADMIN

  React.useEffect(() => {
    if (!user) {
      fetchCurrentUser().catch(() => {})
    }
  }, [user, fetchCurrentUser])

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error("Vui lòng điền đầy đủ các trường thông tin")
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error("Mật khẩu mới và xác nhận mật khẩu không khớp")
      return
    }
    if (newPassword.length < 6) {
      toast.error("Mật khẩu mới phải có ít nhất 6 ký tự")
      return
    }

    setIsLoading(true)
    try {
      await userService.changePassword(currentPassword, newPassword)
      toast.success("Đổi mật khẩu thành công! Vui lòng sử dụng mật khẩu mới cho lần đăng nhập sau.")
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err) {
      toast.error("Đổi mật khẩu thất bại", {
        description: err instanceof Error ? err.message : "Mật khẩu hiện tại không chính xác.",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-4 sm:p-6">
      {/* Header */}
      <div>
        <h1 className="font-heading text-xl font-bold tracking-tight text-heading">
          {isAdmin ? "Hồ sơ Quản trị viên" : "Hồ sơ cá nhân"}
        </h1>
        <p className="mt-1 text-xs text-muted">
          {isAdmin
            ? "Thông tin quyền hạn và cấu hình bảo mật tài khoản quản trị hệ thống HUCE KMS"
            : "Quản lý thông tin tài khoản và bảo mật của bạn trong hệ thống HUCE KMS"}
        </p>
      </div>

      {/* Account Info Card */}
      <Card className="border-border shadow-xs">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="flex items-center gap-2">
            {isAdmin ? (
              <ShieldCheck className="h-5 w-5 text-brand-primary" />
            ) : (
              <User className="h-5 w-5 text-brand-primary" />
            )}
            <div>
              <CardTitle className="text-base font-bold text-heading">
                {isAdmin ? "Thông tin Quản trị viên" : "Thông tin tài khoản"}
              </CardTitle>
              <CardDescription className="text-xs">
                {isAdmin
                  ? "Tài khoản có toàn quyền quản lý dữ liệu tri thức, tài khoản và hệ thống crawler"
                  : "Thông tin định danh liên kết từ hệ thống HUCE-KMS"}
              </CardDescription>
            </div>
          </div>
          <Badge
            variant={isAdmin ? "default" : "secondary"}
            className={isAdmin ? "bg-brand-primary text-white" : ""}
          >
            {user?.role ? ROLE_LABELS[user.role] : "Người dùng"}
          </Badge>
        </CardHeader>

        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div>
            <Label className="text-muted">Họ và tên</Label>
            <p className="mt-1 text-sm font-semibold text-heading">
              {user?.full_name || "Chưa cập nhật"}
            </p>
          </div>
          <div>
            <Label className="text-muted">{isAdmin ? "Tên đăng nhập" : "Tên tài khoản"}</Label>
            <p className="mt-1 font-mono text-sm font-semibold text-heading">
              {user?.username || "—"}
            </p>
          </div>
          <div>
            <Label className="text-muted">{isAdmin ? "Email quản trị" : "Email liên hệ"}</Label>
            <p className="mt-1 text-sm font-semibold text-heading">{user?.email || "—"}</p>
          </div>
          <div>
            <Label className="text-muted">Trạng thái tài khoản</Label>
            <p className="mt-1 text-sm font-semibold text-emerald-600">
              {user?.is_active !== false ? "Đang hoạt động" : "Bị khóa"}
            </p>
          </div>
        </CardContent>

        <CardFooter className="flex items-center justify-between border-t border-border/50 pt-4">
          <span className="text-xs text-muted">
            {isAdmin ? "Phiên làm việc bảo mật cao" : "Đã xác thực định danh"}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => logout()}
            className="text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-border"
          >
            <LogOut className="mr-1.5 h-3.5 w-3.5" />
            Đăng xuất tài khoản
          </Button>
        </CardFooter>
      </Card>

      {/* Security / Password Change Card */}
      <Card className="border-border shadow-xs">
        <CardHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-brand-primary" />
            <CardTitle className="text-base font-bold text-heading">
              {isAdmin ? "Đổi mật khẩu Quản trị" : "Đổi mật khẩu"}
            </CardTitle>
          </div>
          <CardDescription className="text-xs">
            {isAdmin
              ? "Yêu cầu đổi mật khẩu định kỳ để đảm bảo an toàn cơ sở tri thức"
              : "Cập nhật mật khẩu để tăng cường tính bảo mật cho tài khoản"}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current-pw" className="text-xs">
                Mật khẩu hiện tại
              </Label>
              <Input
                id="current-pw"
                type="password"
                placeholder="Nhập mật khẩu hiện tại"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="new-pw" className="text-xs">
                  Mật khẩu mới
                </Label>
                <Input
                  id="new-pw"
                  type="password"
                  placeholder="Nhập mật khẩu mới"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm-pw" className="text-xs">
                  Xác nhận mật khẩu mới
                </Label>
                <Input
                  id="confirm-pw"
                  type="password"
                  placeholder="Nhập lại mật khẩu mới"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isLoading}
                />
              </div>
            </div>

            <Button
              type="submit"
              size="sm"
              className="bg-brand-primary text-white hover:bg-brand-primary-hover"
              disabled={isLoading}
            >
              <Check className="mr-1.5 h-4 w-4" />
              {isLoading ? "Đang xử lý..." : "Cập nhật mật khẩu"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
