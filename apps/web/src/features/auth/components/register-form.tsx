"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter } from "next/navigation"
import { User, Mail, Lock } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "@/components/ui/sonner"
import { PasswordChecklist } from "./password-checklist"
import { ROUTES } from "@/constants/routes"
import { authService } from "@/features/auth/services/auth-service"

const registerSchema = z
  .object({
    full_name: z.string().min(2, "Họ và tên tối thiểu 2 ký tự"),
    username: z
      .string()
      .min(3, "Tên đăng nhập tối thiểu 3 ký tự")
      .regex(/^[a-zA-Z0-9_.-]+$/, "Tên đăng nhập chỉ gồm chữ cái, chữ số, gạch dưới hoặc chấm"),
    email: z.string().email("Địa chỉ email không hợp lệ"),
    password: z
      .string()
      .min(8, "Mật khẩu tối thiểu 8 ký tự")
      .regex(/[A-Z]/, "Cần chứa ít nhất 1 chữ hoa")
      .regex(/[0-9]/, "Cần chứa ít nhất 1 chữ số")
      .regex(/[^A-Za-z0-9]/, "Cần chứa ít nhất 1 ký tự đặc biệt"),
    confirm_password: z.string().min(1, "Vui lòng nhập lại mật khẩu"),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Mật khẩu xác nhận không khớp",
    path: ["confirm_password"],
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
    defaultValues: { full_name: "", username: "", email: "", password: "", confirm_password: "" },
  })

  const passwordValue = watch("password") || ""

  const onSubmit = async (values: RegisterFormValues) => {
    setIsLoading(true)
    try {
      await authService.register({
        full_name: values.full_name,
        username: values.username,
        email: values.email,
        password: values.password,
      })

      toast.success("Đăng ký tài khoản thành công!", {
        description: `Chào mừng ${values.full_name}, vui lòng đăng nhập để bắt đầu.`,
      })
      router.push(ROUTES.AUTH.LOGIN)
    } catch (err) {
      let errorMsg = "Đăng ký không thành công. Vui lòng thử lại."
      if (err instanceof Error) {
        const msg = err.message.toLowerCase()
        if (msg.includes("username") || msg.includes("tên đăng nhập")) {
          errorMsg = "Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên khác."
        } else if (msg.includes("email")) {
          errorMsg = "Địa chỉ email này đã được đăng ký tài khoản."
        } else if (msg.includes("network") || msg.includes("failed to fetch")) {
          errorMsg = "Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng."
        } else {
          errorMsg = err.message
        }
      }
      toast.error("Đăng ký thất bại", {
        description: errorMsg,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Họ và tên */}
      <div className="space-y-1.5">
        <Label htmlFor="full_name">Họ và tên</Label>
        <div className="relative">
          <Input
            id="full_name"
            placeholder="Ví dụ: Nguyễn Văn A"
            {...register("full_name")}
            disabled={isLoading}
            className="pl-9"
          />
          <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
      </div>

      {/* Tên đăng nhập */}
      <div className="space-y-1.5">
        <Label htmlFor="username">Tên đăng nhập</Label>
        <div className="relative">
          <Input
            id="username"
            placeholder="Ví dụ: nguyenvana"
            {...register("username")}
            disabled={isLoading}
            className="pl-9"
          />
          <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
      </div>

      {/* Email */}
      <div className="space-y-1.5">
        <Label htmlFor="email">Email</Label>
        <div className="relative">
          <Input
            id="email"
            type="email"
            placeholder="name@example.com"
            {...register("email")}
            disabled={isLoading}
            className="pl-9"
          />
          <Mail className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
      </div>

      {/* Mật khẩu */}
      <div className="space-y-1.5">
        <Label htmlFor="password">Mật khẩu</Label>
        <div className="relative">
          <Input
            id="password"
            type="password"
            placeholder="Nhập mật khẩu"
            {...register("password")}
            disabled={isLoading}
            className="pl-9"
          />
          <Lock className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>

      {/* Password Rule Checklist - Only visible when user begins typing password */}
      {passwordValue.length > 0 && <PasswordChecklist password={passwordValue} />}

      {/* Xác nhận mật khẩu */}
      <div className="space-y-1.5">
        <Label htmlFor="confirm_password">Xác nhận mật khẩu</Label>
        <div className="relative">
          <Input
            id="confirm_password"
            type="password"
            placeholder="Nhập lại mật khẩu để xác nhận"
            {...register("confirm_password")}
            disabled={isLoading}
            className="pl-9"
          />
          <Lock className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.confirm_password && (
          <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
        )}
      </div>

      {/* Nút Đăng ký */}
      <Button
        type="submit"
        className="mt-2 w-full font-semibold"
        loading={isLoading}
        loadingText="Đang xử lý..."
      >
        Đăng ký tài khoản
      </Button>
    </form>
  )
}
