// LogRaven — User TypeScript Types

export interface User {
  id: string
  email: string
  tier: 'free' | 'pro' | 'team'
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
