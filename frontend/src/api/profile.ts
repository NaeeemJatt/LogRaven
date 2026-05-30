import client from './client'

export interface UpdateProfileRequest {
  name?: string
  timezone?: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

export const profileApi = {
  updateProfile: (data: UpdateProfileRequest) =>
    client.patch('/auth/me', data),

  changePassword: (data: ChangePasswordRequest) =>
    client.post('/auth/password/change', data),
}
