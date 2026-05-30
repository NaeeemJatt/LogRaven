import { useMutation } from '@tanstack/react-query'
import { profileApi } from '../api/profile'

export function useProfile() {
  const updateProfileMutation = useMutation({
    mutationFn: profileApi.updateProfile,
  })

  const changePasswordMutation = useMutation({
    mutationFn: profileApi.changePassword,
  })

  return {
    updateProfile: updateProfileMutation.mutateAsync,
    isUpdatingProfile: updateProfileMutation.isPending,
    profileError: updateProfileMutation.error,

    changePassword: changePasswordMutation.mutateAsync,
    isChangingPassword: changePasswordMutation.isPending,
    passwordError: changePasswordMutation.error,
  }
}
