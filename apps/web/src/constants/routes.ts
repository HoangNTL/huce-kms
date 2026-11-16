/**
 * HUCE KMS - Centralized Route Definitions
 */
export const ROUTES = {
  HOME: "/",
  AUTH: {
    LOGIN: "/login",
    REGISTER: "/register",
    FORGOT_PASSWORD: "/forgot-password",
  },
  USER: {
    CHAT: "/chat",
    CHAT_DETAIL: (id: string) => `/chat/${id}`,
    PROFILE: "/profile",
  },
  ADMIN: {
    ROOT: "/admin",
    DASHBOARD: "/admin/dashboard",
    USERS: "/admin/users",
    DOCUMENTS: "/admin/documents",
    DOCUMENT_DETAIL: (id: string) => `/admin/documents/${id}`,
    CATEGORIES: "/admin/categories",
    CRAWLER: "/admin/crawler",
    PROFILE: "/admin/profile",
  },
} as const
