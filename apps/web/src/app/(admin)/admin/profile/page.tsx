import * as React from "react"
import { Metadata } from "next"
import { ProfileView } from "@/features/users"

export const metadata: Metadata = {
  title: "Tài khoản | HUCE KMS",
  description: "Quản lý thông tin tài khoản và bảo mật",
}

export default function AdminProfilePage() {
  return <ProfileView />
}
