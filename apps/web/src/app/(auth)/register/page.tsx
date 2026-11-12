import * as React from "react"
import Link from "next/link"
import { Metadata } from "next"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { RegisterForm } from "@/features/auth"
import { ROUTES } from "@/constants/routes"

export const metadata: Metadata = {
  title: "Đăng ký | HUCE KMS",
  description: "Đăng ký tài khoản hệ thống HUCE KMS",
}

export default function RegisterPage() {
  return (
    <Card className="border-border shadow-xs">
      <CardHeader className="text-center pb-2">
        <CardTitle className="font-heading text-xl font-bold text-heading">
          Tạo tài khoản
        </CardTitle>
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
