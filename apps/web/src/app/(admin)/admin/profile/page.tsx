"use client"

import * as React from "react"
import Link from "next/link"
import { ShieldCheck, LogOut, KeyRound, Check } from "lucide-react"
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
import { ROUTES } from "@/constants/routes"

export default function AdminProfilePage() {
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
      toast.success("Đổi mật khẩu Quản trị viên thành công!")
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
    <div className="max-w-4xl space-y-6">
      <div>
        <h2 className="font-heading text-xl font-bold text-heading">Hồ sơ Quản trị viên</h2>
        <p className="text-xs text-muted">
          Thông tin quyền hạn và cấu hình bảo mật tài khoản quản trị hệ thống HUCE KMS
        </p>
      </div>

      {/* Admin Info */}
      <Card className="border-border shadow-xs">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-brand-primary" />
              <CardTitle className="text-base font-bold text-heading">
                Thông tin Quản trị viên
              </CardTitle>
            </div>
            <Badge variant="default" className="bg-brand-primary text-[11px] text-white">
              Super Admin
            </Badge>
          </div>
          <CardDescription className="text-xs">
            Tài khoản có toàn quyền quản lý dữ liệu tri thức, tài khoản và hệ thống crawler
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-2">
          <div>
            <Label className="text-muted">Họ và tên</Label>
            <p className="mt-1 text-sm font-semibold text-heading">Quản trị viên Hệ thống</p>
          </div>
          <div>
            <Label className="text-muted">Tên đăng nhập</Label>
            <p className="mt-1 font-mono text-sm font-semibold text-heading">admin_huce</p>
          </div>
          <div>
            <Label className="text-muted">Email quản trị</Label>
            <p className="mt-1 text-sm font-semibold text-heading">admin@huce.edu.vn</p>
          </div>
          <div>
            <Label className="text-muted">Đơn vị quản lý</Label>
            <p className="mt-1 text-sm font-semibold text-heading">
              Trung tâm CNTT & Thư viện HUCE
            </p>
          </div>
        </CardContent>
        <CardFooter className="flex items-center justify-between border-t border-border/50 pt-4">
          <span className="text-xs text-muted">Phiên làm việc bảo mật cao</span>
          <Link href={ROUTES.AUTH.LOGIN}>
            <Button
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs text-destructive hover:bg-destructive/10"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Đăng xuất tài khoản</span>
            </Button>
          </Link>
        </CardFooter>
      </Card>

      {/* Security / Password */}
      <Card className="border-border shadow-xs">
        <CardHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-brand-primary" />
            <CardTitle className="text-base font-bold text-heading">
              Đổi mật khẩu Quản trị
            </CardTitle>
          </div>
          <CardDescription className="text-xs">
            Yêu cầu đổi mật khẩu định kỳ 90 ngày để đảm bảo an toàn cơ sở tri thức
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleChangePassword}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="admin-curr-pw" className="text-xs">
                Mật khẩu hiện tại
              </Label>
              <Input
                id="admin-curr-pw"
                type="password"
                placeholder="Nhập mật khẩu quản trị hiện tại"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="text-xs"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="admin-new-pw" className="text-xs">
                  Mật khẩu mới
                </Label>
                <Input
                  id="admin-new-pw"
                  type="password"
                  placeholder="Nhập mật khẩu mới"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="text-xs"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="admin-confirm-pw" className="text-xs">
                  Xác nhận mật khẩu mới
                </Label>
                <Input
                  id="admin-confirm-pw"
                  type="password"
                  placeholder="Nhập lại mật khẩu mới"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="text-xs"
                />
              </div>
            </div>
          </CardContent>
          <CardFooter className="border-t border-border/50 pt-4">
            <Button
              type="submit"
              disabled={isLoading}
              className="gap-1.5 bg-brand-primary text-xs text-white hover:bg-brand-primary-hover"
            >
              <Check className="h-3.5 w-3.5" />
              {isLoading ? "Đang lưu..." : "Cập nhật mật khẩu"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
