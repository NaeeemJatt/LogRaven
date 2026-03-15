// LogRaven — Investigations API Functions
// All investigation and file upload API calls.
// TODO Month 1 Week 3: Implement.

import client from './client'

export const investigationsApi = {
  create: (name: string) =>
    client.post('/api/v1/investigations', { name }),
  list: (page = 1, limit = 20) =>
    client.get('/api/v1/investigations', { params: { page, limit } }),
  get: (id: string) =>
    client.get(`/api/v1/investigations/${id}`),
  uploadFile: (id: string, file: File, sourceType: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    return client.post(`/api/v1/investigations/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  removeFile: (id: string, fileId: string) =>
    client.delete(`/api/v1/investigations/${id}/files/${fileId}`),
  analyze: (id: string) =>
    client.post(`/api/v1/investigations/${id}/analyze`),
  getStatus: (id: string) =>
    client.get(`/api/v1/investigations/${id}/status`),
}
