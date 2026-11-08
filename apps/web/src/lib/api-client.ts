export interface ApiRequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

/**
 * Standardized Fetch Client for HUCE KMS FastAPI Backend
 */
export async function apiClient<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
  const { params, headers, ...restOptions } = options

  let url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`

  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value))
      }
    })
    const queryString = searchParams.toString()
    if (queryString) {
      url += (url.includes("?") ? "&" : "?") + queryString
    }
  }

  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null
  const isFormData = typeof FormData !== "undefined" && restOptions.body instanceof FormData

  const defaultHeaders: HeadersInit = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  }

  const response = await fetch(url, {
    headers: defaultHeaders,
    ...restOptions,
  })

  // Handle 401 Unauthorized (attempt token refresh if on client)
  if (response.status === 401 && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("refresh_token")
    if (refreshToken) {
      try {
        const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (refreshResponse.ok) {
          const { access_token } = await refreshResponse.json()
          localStorage.setItem("access_token", access_token)

          // Retry original request with new token
          const retryHeaders = {
            ...defaultHeaders,
            Authorization: `Bearer ${access_token}`,
          }
          const retryResponse = await fetch(url, {
            headers: retryHeaders,
            ...restOptions,
          })

          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => null)
            throw new ApiError(
              errorData?.detail || `API Error: ${retryResponse.statusText}`,
              retryResponse.status,
              errorData
            )
          }

          return (await retryResponse.json()) as T
        } else {
          // Token expired completely -> Clear storage
          localStorage.removeItem("access_token")
          localStorage.removeItem("refresh_token")
        }
      } catch {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
      }
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => null)
    throw new ApiError(
      errorData?.detail || `API Error: ${response.statusText}`,
      response.status,
      errorData
    )
  }

  if (response.status === 204) {
    return {} as T
  }

  return (await response.json()) as T
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

apiClient.delete = function <T>(endpoint: string, options?: ApiRequestOptions): Promise<T> {
  return apiClient<T>(endpoint, { method: "DELETE", ...options })
}
