"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter } from "next/navigation"
import { User, Mail, Lock, UserCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "@/components/ui/sonner"
import { PasswordChecklist } from "./password-checklist"
import { ROUTES } from "@/constants/routes"

const registerSchema = z.object({
  fullName: z.string().min(2, "Họ và tên tối thiểu 2 ký tự"),
  username: z.string().min(3, "Tên đăng nhập tối thiểu 3 ký tự"),
  email: z
    .string()
    .email("Email không hợp lệ")
    .endsWith("@huce.edu.vn", "Vui lòng sử dụng email đuôi @huce.edu.vn"),
  password: z
    .string()
    .min(8, "Mật khẩu tối thiểu 8 ký tự")
    .regex(/[A-Z]/, "Cần chứa ít nhất 1 chữ hoa")
    .regex(/[0-9]/, "Cần chứa ít nhất 1 chữ số")
    .regex(/[^A-Za-z0-9]/, "Cần chứa ít nhất 1 ký tự đặc biệt"),
})

type RegisterFormValues = z.infer<typeof registerSchema>

export function RegisterForm() {
  const [isLoading, setIsLoading] = React.useState(false)
  const router = useRouter()

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { fullName: "", username: "", email: "", password: "" },
  })

  const passwordValue = watch("password") || ""

  const onSubmit = async (values: RegisterFormValues) => {
    setIsLoading(true)
    try {
      await new Promise((res) => setTimeout(res, 800))
      toast.success("Đăng ký tài khoản thành công!", {
        description: `Chào mừng ${values.fullName}, vui lòng đăng nhập để tiếp tục.`,
      })
      router.push(ROUTES.AUTH.LOGIN)
    } catch {
      toast.error("Đăng ký thất bại", {
        description: "Email hoặc tên đăng nhập có thể đã tồn tại.",
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="fullName">Họ và tên</Label>
        <div className="relative">
          <Input
            id="fullName"
            placeholder="Nguyễn Văn A"
            {...register("fullName")}
            disabled={isLoading}
            className="pl-9"
          />
          <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.fullName && <p className="text-xs text-destructive">{errors.fullName.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="username">Tên đăng nhập</Label>
        <div className="relative">
          <Input
            id="username"
            placeholder="nguyenvana"
            {...register("username")}
            disabled={isLoading}
            className="pl-9"
          />
          <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="email">Email sinh viên / cán bộ</Label>
        <div className="relative">
          <Input
            id="email"
            type="email"
            placeholder="tensinhvien@huce.edu.vn"
            {...register("email")}
            disabled={isLoading}
            className="pl-9"
          />
          <Mail className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="password">Mật khẩu</Label>
        <div className="relative">
          <Input
            id="password"
            type="password"
            placeholder="Nhập mật khẩu an toàn"
            {...register("password")}
            disabled={isLoading}
            className="pl-9"
          />
          <Lock className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>

      <PasswordChecklist password={passwordValue} />

      <Button
        type="submit"
        className="mt-2 w-full bg-brand-primary text-white hover:bg-brand-primary-hover"
        disabled={isLoading}
      >
        <UserCheck className="mr-2 h-4 w-4" />
        {isLoading ? "Đang tạo tài khoản..." : "Đăng ký tài khoản"}
      </Button>
    </form>
  )
}
