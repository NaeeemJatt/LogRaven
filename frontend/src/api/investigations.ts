// LogRaven — Investigations API Functions
import client from './client'

export const investigationsApi = {
  create: (name: string) =>
    client.post('/api/v1/investigations', { name }),

  list: (page = 1, limit = 20) =>
    client.get('/api/v1/investigations', { params: { page, limit } }),

  get: (id: string) =>
    client.get(`/api/v1/investigations/${id}`),

  delete: (id: string) =>
    client.delete(`/api/v1/investigations/${id}`),

  uploadFile: (id: string, file: File, sourceType: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('source_type', sourceType)
    return client.post(`/api/v1/investigations/${id}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  deleteFile: (id: string, fileId: string) =>
    client.delete(`/api/v1/investigations/${id}/files/${fileId}`),

  analyze: (id: string) =>
    client.post(`/api/v1/investigations/${id}/analyze`),

  getStatus: (id: string) =>
    client.get(`/api/v1/investigations/${id}/status`),

  getReport: (id: string) =>
    client.get(`/api/v1/investigations/${id}/report`),

  getReportDownload: (id: string) =>
    client.get(`/api/v1/investigations/${id}/report/download`),
}
