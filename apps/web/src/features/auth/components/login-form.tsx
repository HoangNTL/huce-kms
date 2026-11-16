"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter, useSearchParams } from "next/navigation"
import { Eye, EyeOff, Lock, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"
import { authService } from "@/features/auth/services/auth-service"
import { useAuthStore } from "@/stores/use-auth-store"
import { USER_ROLES } from "@/types/user"

const loginSchema = z.object({
  username: z.string().min(3, "Tên đăng nhập tối thiểu 3 ký tự"),
  password: z.string().min(6, "Mật khẩu tối thiểu 6 ký tự"),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginForm() {
  const [showPassword, setShowPassword] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const router = useRouter()
  const searchParams = useSearchParams()
  const setAuth = useAuthStore((state) => state.setAuth)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  })

  const onSubmit = async (values: LoginFormValues) => {
    setIsLoading(true)
    try {
      const response = await authService.login(values)
      setAuth(response)

      const role = String(response.user.role || "").toLowerCase()
      const displayName = response.user.full_name || response.user.username

      toast.success("Đăng nhập thành công!", {
        description: `Chào mừng bạn quay trở lại, ${displayName}!`,
      })

      const from = searchParams.get("from")
      if (from && from.startsWith("/")) {
        router.push(from)
      } else if (role === USER_ROLES.ADMIN) {
        router.push(ROUTES.ADMIN.DASHBOARD)
      } else {
        router.push(ROUTES.USER.CHAT)
      }
    } catch (err) {
      let errorMsg = "Tên đăng nhập, email hoặc mật khẩu không chính xác."
      if (err instanceof Error) {
        const msg = err.message.toLowerCase()
        if (msg.includes("invalid username") || msg.includes("password") || msg.includes("credentials")) {
          errorMsg = "Tên đăng nhập, email hoặc mật khẩu không chính xác."
        } else if (msg.includes("deactivated") || msg.includes("inactive") || msg.includes("khóa")) {
          errorMsg = "Tài khoản của bạn đã bị khóa hoặc ngừng hoạt động."
        } else if (msg.includes("network") || msg.includes("failed to fetch")) {
          errorMsg = "Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại mạng."
        } else {
          errorMsg = err.message
        }
      }
      toast.error("Đăng nhập thất bại", {
        description: errorMsg,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="username">Tên đăng nhập hoặc Email</Label>
        <div className="relative">
          <Input
            id="username"
            placeholder="Nhập tên đăng nhập hoặc email"
            {...register("username")}
            disabled={isLoading}
            className="pl-9"
          />
          <User className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
        </div>
        {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="password">Mật khẩu</Label>
        </div>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? "text" : "password"}
            placeholder="Nhập mật khẩu"
            {...register("password")}
            disabled={isLoading}
            className="pr-9 pl-9"
          />
          <Lock className="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-muted" />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute top-2.5 right-3 text-muted hover:text-heading"
            aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
      </div>

      <Button
        type="submit"
        className="mt-2 w-full font-semibold"
        loading={isLoading}
        loadingText="Đang xử lý..."
      >
        Đăng nhập
      </Button>
    </form>
  )
}
