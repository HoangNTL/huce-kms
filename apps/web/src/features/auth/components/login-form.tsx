"use client"

import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { useRouter } from "next/navigation"
import { Eye, EyeOff, Lock, User, LogIn } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "@/components/ui/sonner"
import { ROUTES } from "@/constants/routes"

const loginSchema = z.object({
  username: z.string().min(3, "Tên đăng nhập tối thiểu 3 ký tự"),
  password: z.string().min(6, "Mật khẩu tối thiểu 6 ký tự"),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginForm() {
  const [showPassword, setShowPassword] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)
  const router = useRouter()

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
      // Simulate login for foundation skeleton
      await new Promise((res) => setTimeout(res, 800))
      toast.success("Đăng nhập thành công!", {
        description: `Chào mừng bạn quay trở lại, ${values.username}!`,
      })
      // Redirect based on dummy role
      if (values.username.toLowerCase().includes("admin")) {
        router.push(ROUTES.ADMIN.DASHBOARD)
      } else {
        router.push(ROUTES.USER.CHAT)
      }
    } catch {
      toast.error("Đăng nhập thất bại", {
        description: "Vui lòng kiểm tra lại tên đăng nhập hoặc mật khẩu.",
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
            placeholder="Nhập tên đăng nhập hoặc email HUCE"
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
        className="mt-2 w-full bg-brand-primary text-white hover:bg-brand-primary-hover"
        disabled={isLoading}
      >
        <LogIn className="mr-2 h-4 w-4" />
        {isLoading ? "Đang xử lý..." : "Đăng nhập"}
      </Button>
    </form>
  )
}
