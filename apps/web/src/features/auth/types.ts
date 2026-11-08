export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  email: string
  fullName: string
  password: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  tokenType: string
}
