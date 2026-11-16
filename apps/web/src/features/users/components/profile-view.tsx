"use client"

import * as React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "@/components/ui/sonner"
import { useAuthStore } from "@/stores/use-auth-store"
import { userService } from "@/features/users/services/user-service"

export function ProfileView() {
  const { user, fetchCurrentUser } = useAuthStore()
  const [currentPassword, setCurrentPassword] = React.useState("")
  const [newPassword, setNewPassword] = React.useState("")
  const [confirmPassword, setConfirmPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)

  React.useEffect(() => {
    if (!user) {
      fetchCurrentUser().catch(() => {})
    }
  }, [user, fetchCurrentUser])

  const handleChangePassword = async (e: React.SubmitEvent<HTMLFormElement>) => {
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
      {/* Header: Clean & Unified */}
      <div>
        <h1 className="font-heading text-2xl font-bold tracking-tight text-heading">
          Tài khoản
        </h1>
      </div>

      {/* Account Info Card */}
      <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0">
        <div className="border-b border-border/50 px-6 py-4">
          <h2 className="text-base font-bold text-heading">
            Thông tin tài khoản
          </h2>
        </div>

        <CardContent className="p-6 grid gap-4 sm:grid-cols-2">
          <div>
            <Label className="text-xs text-muted">Họ và tên</Label>
            <p className="mt-1 text-sm font-semibold text-heading">
              {user?.full_name || "Chưa cập nhật"}
            </p>
          </div>
          <div>
            <Label className="text-xs text-muted">Tên đăng nhập</Label>
            <p className="mt-1 font-mono text-sm font-semibold text-heading">
              {user?.username || "—"}
            </p>
          </div>
          <div>
            <Label className="text-xs text-muted">Email</Label>
            <p className="mt-1 text-sm font-semibold text-heading">{user?.email || "—"}</p>
          </div>
          <div>
            <Label className="text-xs text-muted">Trạng thái tài khoản</Label>
            <p className="mt-1 text-sm font-semibold text-emerald-600">
              {user?.is_active !== false ? "Đang hoạt động" : "Bị khóa"}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Security / Password Change Card */}
      <Card className="rounded-2xl border border-slate-200/80 bg-surface shadow-xs py-0 gap-0">
        <div className="border-b border-border/50 px-6 py-4">
          <h2 className="text-base font-bold text-heading">
            Đổi mật khẩu
          </h2>
        </div>

        <CardContent className="p-6">
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
                className="rounded-lg text-xs"
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
                  className="rounded-lg text-xs"
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
                  className="rounded-lg text-xs"
                />
              </div>
            </div>

            <Button
              type="submit"
              size="sm"
              loading={isLoading}
              loadingText="Đang xử lý..."
            >
              Đổi mật khẩu
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
