import * as React from "react"
import { Metadata } from "next"
import { ProfileView } from "@/features/users"

export const metadata: Metadata = {
  title: "Hồ sơ cá nhân | HUCE KMS",
  description: "Quản lý thông tin tài khoản và bảo mật cá nhân",
}

export default function UserProfilePage() {
  return <ProfileView />
}
