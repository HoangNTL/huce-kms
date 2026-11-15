import type { Metadata } from "next"
import { Toaster } from "@/components/ui/sonner"
import "./globals.css"

export const metadata: Metadata = {
  title: "HUCE KMS - Hệ thống Quản trị Tri thức và Trợ lý AI",
  description: "Hệ thống Quản trị Tri thức và Trợ lý AI Trường Đại học Xây dựng Hà Nội",
  icons: {
    icon: "/huce-logo.svg",
    shortcut: "/huce-logo.svg",
    apple: "/huce-logo.svg",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" className="h-full">
      <head>
        <link rel="icon" href="/huce-logo.svg" type="image/svg+xml" sizes="any" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap"
        />
      </head>
      <body className="antialiased">
        {children}
        <Toaster position="top-right" richColors />
      </body>
    </html>
  )
}
