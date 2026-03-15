// LogRaven — Reports API Functions
// TODO Month 4 Week 1: Implement.

import client from './client'

export const reportsApi = {
  get: (id: string) =>
    client.get(`/api/v1/reports/${id}`),
  getDownloadUrl: (id: string) =>
    client.get(`/api/v1/reports/${id}/download`),
}
