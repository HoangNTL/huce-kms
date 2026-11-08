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
import { RegisterForm } from "@/features/auth"
import { ROUTES } from "@/constants/routes"

export const metadata: Metadata = {
  title: "Đăng ký | HUCE KMS",
  description: "Đăng ký tài khoản sinh viên Trường Đại học Xây dựng Hà Nội",
}

export default function RegisterPage() {
  return (
    <Card className="border-border shadow-xs">
      <CardHeader className="space-y-1 text-center">
        <CardTitle className="font-heading text-xl font-bold text-heading">
          Đăng ký tài khoản mới
        </CardTitle>
        <CardDescription className="text-xs">
          Dành cho sinh viên, giảng viên và cán bộ Trường Đại học Xây dựng Hà Nội
        </CardDescription>
      </CardHeader>

      <CardContent>
        <RegisterForm />
      </CardContent>

      <CardFooter className="flex flex-col gap-2 border-t border-border/50 pt-4 text-center text-xs text-muted">
        <div>
          <span>Đã có tài khoản? </span>
          <Link href={ROUTES.AUTH.LOGIN} className="font-medium text-brand-primary hover:underline">
            Đăng nhập ngay
          </Link>
        </div>
      </CardFooter>
    </Card>
  )
}
