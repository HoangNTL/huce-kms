/**
 * HUCE KMS - Site & Brand Configuration
 */
export const siteConfig = {
  name: "HUCE KMS",
  shortName: "KMS",
  fullName: "Hệ thống Quản trị Tri thức & Trợ lý AI",
  institution: "Trường Đại học Xây dựng Hà Nội (HUCE)",
  description:
    "Nền tảng tra cứu tri thức học thuật, quy chế đào tạo và văn bản chính thức tích hợp trợ lý AI thông minh cho Trường Đại học Xây dựng Hà Nội.",
  brandColor: "#0F5BA6",
  links: {
    portal: "https://huce.edu.vn",
  },
} as const

export type SiteConfig = typeof siteConfig
