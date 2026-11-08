"use client"

import * as React from "react"
import { User, KeyRound, Check } from "lucide-react"
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

export default function UserProfilePage() {
  const [currentPassword, setCurrentPassword] = React.useState("")
  const [newPassword, setNewPassword] = React.useState("")
  const [confirmPassword, setConfirmPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)

  const handleChangePassword = async (e: React.SubmitEvent) => {
    e.preventDefault()
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error("Vui lòng điền đầy đủ các trường thông tin")
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error("Mật khẩu mới và xác nhận mật khẩu không khớp")
      return
    }

    setIsLoading(true)
    try {
      await new Promise((res) => setTimeout(res, 800))
      toast.success("Đổi mật khẩu thành công!")
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch {
      toast.error("Đổi mật khẩu thất bại")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-4 sm:p-6 lg:p-8">
      <div>
        <h1 className="font-heading text-2xl font-bold text-heading">Hồ sơ cá nhân</h1>
        <p className="text-xs text-muted">
          Quản lý thông tin tài khoản và bảo mật của bạn trong hệ thống HUCE KMS
        </p>
      </div>

      {/* Account Info Card */}
      <Card className="border-border shadow-xs">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-brand-primary" />
              <CardTitle className="text-base font-bold text-heading">
                Thông tin tài khoản
              </CardTitle>
            </div>
            <Badge
              variant="outline"
              className="border-brand-primary/30 bg-brand-primary/5 text-brand-primary"
            >
              Sinh viên chính quy
            </Badge>
          </div>
          <CardDescription>Thông tin định danh liên kết từ hệ thống trường</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-2">
          <div>
            <Label className="text-muted">Họ và tên</Label>
            <p className="mt-1 text-sm font-semibold text-heading">Nguyễn Văn A</p>
          </div>
          <div>
            <Label className="text-muted">Mã sinh viên</Label>
            <p className="mt-1 text-sm font-semibold text-heading">0123456</p>
          </div>
          <div>
            <Label className="text-muted">Email liên hệ</Label>
            <p className="mt-1 text-sm font-semibold text-heading">0123456@huce.edu.vn</p>
          </div>
          <div>
            <Label className="text-muted">Khoa / Bộ môn</Label>
            <p className="mt-1 text-sm font-semibold text-heading">Khoa Công nghệ Thông tin</p>
          </div>
        </CardContent>
      </Card>

      {/* Security / Password Card */}
      <Card className="border-border shadow-xs">
        <CardHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-brand-primary" />
            <CardTitle className="text-base font-bold text-heading">Đổi mật khẩu</CardTitle>
          </div>
          <CardDescription>
            Cập nhật mật khẩu để tăng cường tính bảo mật cho tài khoản
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleChangePassword}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="current-pw">Mật khẩu hiện tại</Label>
              <Input
                id="current-pw"
                type="password"
                placeholder="Nhập mật khẩu hiện tại"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="new-pw">Mật khẩu mới</Label>
                <Input
                  id="new-pw"
                  type="password"
                  placeholder="Nhập mật khẩu mới"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm-pw">Xác nhận mật khẩu mới</Label>
                <Input
                  id="confirm-pw"
                  type="password"
                  placeholder="Nhập lại mật khẩu mới"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="border-t border-border/50 pt-4">
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
            >
              <Check className="mr-1.5 h-4 w-4" />
              {isLoading ? "Đang lưu..." : "Cập nhật mật khẩu"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
