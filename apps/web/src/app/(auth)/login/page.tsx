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
import { LoginForm } from "@/features/auth"
import { ROUTES } from "@/constants/routes"
import { LoadingSpinner } from "@/components/shared/loading-spinner"

export const metadata: Metadata = {
  title: "Đăng nhập | HUCE KMS",
  description:
    "Đăng nhập vào Hệ thống Quản trị Tri thức và Trợ lý AI Trường Đại học Xây dựng Hà Nội",
}

export default function LoginPage() {
  return (
    <Card className="border-border shadow-xs">
      <CardHeader className="text-center pb-2">
        <CardTitle className="font-heading text-xl font-bold text-heading">
          Đăng nhập hệ thống
        </CardTitle>
      </CardHeader>

      <CardContent>
        <React.Suspense
          fallback={
            <div className="flex h-40 items-center justify-center">
              <LoadingSpinner size="md" label="Đang tải giao diện..." />
            </div>
          }
        >
          <LoginForm />
        </React.Suspense>
      </CardContent>

      <CardFooter className="flex flex-col gap-2 border-t border-border/50 pt-4 text-center text-xs text-muted">
        <div>
          <span>Chưa có tài khoản? </span>
          <Link
            href={ROUTES.AUTH.REGISTER}
            className="font-medium text-brand-primary hover:underline"
          >
            Đăng ký tài khoản
          </Link>
        </div>
      </CardFooter>
    </Card>
  )
}
