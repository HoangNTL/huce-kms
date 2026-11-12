import * as React from "react"
import { Metadata } from "next"
import { ProfileView } from "@/features/users"

export const metadata: Metadata = {
  title: "Hồ sơ Quản trị viên | HUCE KMS",
  description: "Quản lý thông tin tài khoản quản trị và bảo mật",
}

export default function AdminProfilePage() {
  return <ProfileView />
}
