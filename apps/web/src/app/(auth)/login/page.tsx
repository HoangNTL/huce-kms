import * as React from "react"
import Link from "next/link"
import { Metadata } from "next"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { LoginForm } from "@/features/auth"
import { ROUTES } from "@/constants/routes"

export const metadata: Metadata = {
  title: "Đăng nhập | HUCE KMS",
  description:
    "Đăng nhập vào Hệ thống Quản trị Tri thức & Trợ lý AI Trường Đại học Xây dựng Hà Nội",
}

export default function LoginPage() {
  return (
    <Card className="border-border shadow-xs">
      <CardHeader className="space-y-1 text-center">
        <CardTitle className="font-heading text-xl font-bold text-heading">
          Đăng nhập tài khoản
        </CardTitle>
        <CardDescription className="text-xs">
          Nhập thông tin xác thực do Trường Đại học Xây dựng Hà Nội cấp
        </CardDescription>
      </CardHeader>

      <CardContent>
        <LoginForm />
      </CardContent>

      <CardFooter className="flex flex-col gap-2 border-t border-border/50 pt-4 text-center text-xs text-muted">
        <div>
          <span>Chưa có tài khoản? </span>
          <Link
            href={ROUTES.AUTH.REGISTER}
            className="font-medium text-brand-primary hover:underline"
          >
            Đăng ký tài khoản sinh viên
          </Link>
        </div>
      </CardFooter>
    </Card>
  )
}
