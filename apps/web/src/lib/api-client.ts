import { tokenStorage } from "./token-storage"
import { API_BASE_URL } from "@/config/env"
import type { AuthTokens } from "@/features/auth/types"

export interface ApiRequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
  skipAuthRefresh?: boolean
}

export class ApiError extends Error {
  status: number
  data?: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.data = data
  }
}

// Callbacks to synchronize with Zustand store without circular dependency
type TokenRefreshedCallback = (tokens: AuthTokens) => void
type TokenExpiredCallback = () => void

let onTokenRefreshed: TokenRefreshedCallback | null = null
let onTokenExpired: TokenExpiredCallback | null = null

export function registerAuthCallbacks(callbacks: {
  onRefreshed?: TokenRefreshedCallback
  onExpired?: TokenExpiredCallback
}) {
  if (callbacks.onRefreshed) onTokenRefreshed = callbacks.onRefreshed
  if (callbacks.onExpired) onTokenExpired = callbacks.onExpired
}

// Concurrency mutex: Only one /auth/refresh in flight at any given time
let refreshPromise: Promise<string | null> | null = null

export async function silentRefreshToken(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      })

      if (!response.ok) {
        tokenStorage.clear()
        onTokenExpired?.()
        return null
      }

      const json = await response.json()
      const data: AuthTokens = json?.data || json
      const newAccessToken = data?.access_token

      if (newAccessToken) {
        tokenStorage.setAccessToken(newAccessToken)
        onTokenRefreshed?.(data)
        return newAccessToken
      }

      tokenStorage.clear()
      onTokenExpired?.()
      return null
    } catch {
      tokenStorage.clear()
      onTokenExpired?.()
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Standardized Fetch Client for HUCE KMS FastAPI Backend
 */
export async function apiClient<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
  const { params, headers, skipAuthRefresh, ...restOptions } = options

  // Normalize endpoint to prevent duplicate /api/v1 prefix
  let cleanEndpoint = endpoint
  if (API_BASE_URL.endsWith("/api/v1") && cleanEndpoint.startsWith("/api/v1")) {
    cleanEndpoint = cleanEndpoint.slice(7)
  }
  if (!cleanEndpoint.startsWith("/")) {
    cleanEndpoint = `/${cleanEndpoint}`
  }

  let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${cleanEndpoint}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value))
      }
    })
    const queryString = searchParams.toString()
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString
    }
  }

  const token = tokenStorage.getAccessToken()
  const isFormData = typeof FormData !== "undefined" && restOptions.body instanceof FormData

  const defaultHeaders: HeadersInit = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  }

  const response = await fetch(url, {
    credentials: "include", // Always attach and receive HttpOnly cookies
    headers: defaultHeaders,
    ...restOptions,
  })

  // Handle 401 Unauthorized (attempt silent token refresh via HttpOnly cookie)
  const isAuthEndpoint =
    cleanEndpoint.includes("/auth/login") ||
    cleanEndpoint.includes("/auth/refresh") ||
    cleanEndpoint.includes("/auth/logout")

  if (response.status === 401 && !skipAuthRefresh && !isAuthEndpoint && typeof window !== "undefined") {
    const newAccessToken = await silentRefreshToken()

    if (newAccessToken) {
      // Retry original request with the freshly issued access token
      const retryHeaders = {
        ...defaultHeaders,
        Authorization: `Bearer ${newAccessToken}`,
      }
      const retryResponse = await fetch(url, {
        credentials: "include",
        headers: retryHeaders,
        ...restOptions,
      })

      if (!retryResponse.ok) {
        const errorData = await retryResponse.json().catch(() => null)
        throw new ApiError(
          errorData?.message || errorData?.detail || `API Error: ${retryResponse.statusText}`,
          retryResponse.status,
          errorData
        )
      }

      if (retryResponse.status === 204) {
        return {} as T
      }

      const retryJson = await retryResponse.json()
      if (
        retryJson &&
        typeof retryJson === "object" &&
        "data" in retryJson &&
        ("code" in retryJson || "success" in retryJson)
      ) {
        if (retryJson.data !== null && retryJson.data !== undefined) {
          return retryJson.data as T
        }
      }
      return retryJson as T
    } else {
      // In cookie also no refresh token (expired / missing / revoked) -> redirect to login
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/login") &&
        !window.location.pathname.startsWith("/register")
      ) {
        const currentPath = window.location.pathname + window.location.search
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = `/login?from=${encodeURIComponent(currentPath)}`
      }
      throw new ApiError("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.", 401)
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    const errorMessage =
      errorData?.message ||
      errorData?.detail ||
      (typeof errorData?.details === "string" ? errorData.details : null) ||
      `API Error: ${response.statusText}`
    throw new ApiError(errorMessage, response.status, errorData)
  }

  if (response.status === 204) {
    return {} as T
  }

  const json = await response.json()

  // Auto-unwrap backend BaseResponse envelope when present
  if (json && typeof json === "object" && "data" in json && ("code" in json || "success" in json)) {
    if (json.data !== null && json.data !== undefined) {
      return json.data as T
    }
  }

  return json as T
}

// Ergonomic HTTP helper methods attached to apiClient
apiClient.get = function <T>(endpoint: string, options?: ApiRequestOptions): Promise<T> {
  return apiClient<T>(endpoint, { method: "GET", ...options })
}

apiClient.post = function <T>(
  endpoint: string,
  body?: unknown,
  options?: ApiRequestOptions
): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData
  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams

  const bodyData =
    isFormData || isUrlSearchParams
      ? (body as BodyInit)
      : body !== undefined
        ? JSON.stringify(body)
        : undefined

  return apiClient<T>(endpoint, {
    method: "POST",
    body: bodyData,
    ...options,
  })
}

apiClient.put = function <T>(
  endpoint: string,
  body?: unknown,
  options?: ApiRequestOptions
): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData
  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams

  const bodyData =
    isFormData || isUrlSearchParams
      ? (body as BodyInit)
      : body !== undefined
        ? JSON.stringify(body)
        : undefined

  return apiClient<T>(endpoint, {
    method: "PUT",
    body: bodyData,
    ...options,
  })
}

apiClient.patch = function <T>(
  endpoint: string,
  body?: unknown,
  options?: ApiRequestOptions
): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData
  const isUrlSearchParams =
    typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams

  const bodyData =
    isFormData || isUrlSearchParams
      ? (body as BodyInit)
      : body !== undefined
        ? JSON.stringify(body)
        : undefined

  return apiClient<T>(endpoint, {
    method: "PATCH",
    body: bodyData,
    ...options,
  })
}

apiClient.delete = function <T>(endpoint: string, options?: ApiRequestOptions): Promise<T> {
  return apiClient<T>(endpoint, { method: "DELETE", ...options })
}
