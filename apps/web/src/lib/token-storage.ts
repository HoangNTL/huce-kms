/**
 * In-memory Token Storage for HUCE-KMS Frontend
 *
 * Stores the short-lived JWT Access Token purely in module memory to mitigate XSS attacks.
 * Never writes Access Token or Refresh Token to localStorage or sessionStorage.
 * The long-lived Refresh Token is managed exclusively via HttpOnly SameSite cookies by the Backend.
 */

let inMemoryAccessToken: string | null = null

export const tokenStorage = {
  getAccessToken(): string | null {
    return inMemoryAccessToken
  },

  setAccessToken(token: string | null): void {
    inMemoryAccessToken = token
  },

  clear(): void {
    inMemoryAccessToken = null
  },
}
