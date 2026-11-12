/**
 * Centralized Environment & API Configuration for HUCE-KMS Web
 */
export const ENV = {
  API_BASE_URL: (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/+$/, ""),
} as const

export const API_BASE_URL = ENV.API_BASE_URL
