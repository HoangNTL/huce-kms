import { create } from "zustand"
import { UserRole, isUserAdmin, type UserProfile } from "@/types/user"
import type { AuthTokens } from "@/features/auth/types"
import { authService } from "@/features/auth/services/auth-service"
import { tokenStorage } from "@/lib/token-storage"
import { registerAuthCallbacks, silentRefreshToken } from "@/lib/api-client"

interface AuthState {
  user: UserProfile | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  isInitialized: boolean
  setAuth: (data: AuthTokens) => void
  setUser: (user: UserProfile | null) => void
  clearAuth: () => void
  logout: () => Promise<void>
  initAuth: () => Promise<boolean>
  fetchCurrentUser: () => Promise<UserProfile | null>
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,

  setAuth: (data: AuthTokens) => {
    const accessToken = data.access_token || null
    tokenStorage.setAccessToken(accessToken)

    const normalizedUser: UserProfile = {
      ...data.user,
      full_name: data.user.full_name || data.user.username,
      role: isUserAdmin(data.user.role) ? UserRole.ADMIN : UserRole.USER,
      is_active: data.user.is_active ?? true,
    }

    set({
      user: normalizedUser,
      accessToken,
      isAuthenticated: !!accessToken,
      isInitialized: true,
      isLoading: false,
    })
  },

  setUser: (user: UserProfile | null) => {
    set({ user, isAuthenticated: !!user && !!get().accessToken })
  },

  clearAuth: () => {
    tokenStorage.clear()
    if (typeof window !== "undefined") {
      try {
        const keysToRemove: string[] = []
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i)
          if (key && (key.startsWith("huce_chat_thread_") || key === "huce_recent_chat_threads")) {
            keysToRemove.push(key)
          }
        }
        keysToRemove.forEach((k) => localStorage.removeItem(k))
      } catch {
        // Ignore storage errors on clear
      }
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isInitialized: true,
      isLoading: false,
    })
  },

  logout: async () => {
    set({ isLoading: true })
    try {
      await authService.logout()
    } catch {
      // Ignore network errors on logout
    } finally {
      get().clearAuth()
    }
  },

  initAuth: async () => {
    if (get().isInitialized && get().accessToken) {
      return true
    }

    set({ isLoading: true })
    try {
      const newToken = await silentRefreshToken()
      if (newToken) {
        set({ isInitialized: true, isLoading: false })
        return true
      }
    } catch {
      // Silent refresh failed
    }

    get().clearAuth()
    return false
  },

  fetchCurrentUser: async () => {
    const token = get().accessToken
    if (!token) {
      const refreshed = await get().initAuth()
      if (!refreshed) return null
    }

    set({ isLoading: true })
    try {
      const user = await authService.getMe()
      const normalizedUser: UserProfile = {
        ...user,
        full_name: user.full_name || user.username,
        role: isUserAdmin(user.role) ? UserRole.ADMIN : UserRole.USER,
        is_active: user.is_active ?? true,
      }
      set({ user: normalizedUser, isAuthenticated: true, isLoading: false })
      return normalizedUser
    } catch {
      get().clearAuth()
      return null
    }
  },
}))

// Wire up apiClient auto-refresh callbacks with Zustand in-memory state
registerAuthCallbacks({
  onRefreshed: (tokens) => {
    useAuthStore.getState().setAuth(tokens)
  },
  onExpired: () => {
    useAuthStore.getState().clearAuth()
  },
})
