// LogRaven — Dashboard Page
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Navbar from '../components/layout/Navbar'
import Badge from '../components/ui/Badge'
import { investigationsApi } from '../api/investigations'
import type { Investigation } from '../types/investigation'

function SkeletonRow() {
  return (
    <tr>
      {[1, 2, 3, 4, 5].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-raven-700 animate-pulse rounded-none" style={{ width: `${[60, 40, 20, 36, 28][i - 1]}%` }} />
        </td>
      ))}
    </tr>
  )
}

export default function Dashboard() {
  const navigate    = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery<Investigation[]>({
    queryKey: ['investigations'],
    queryFn: async () => {
      const res = await investigationsApi.list()
      return res.data
    },
  })

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this investigation?')) return
    await investigationsApi.delete(id)
    queryClient.invalidateQueries({ queryKey: ['investigations'] })
  }

  return (
    <div className="min-h-screen bg-raven-900">
      <Navbar />

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-white text-xl font-semibold tracking-tight">Investigations</h1>
          <button
            onClick={() => navigate('/investigations/new')}
            className="border border-electric-500 text-electric-500 text-xs px-4 py-1.5 rounded-none hover:bg-electric-900 transition-colors tracking-wide uppercase"
          >
            + New Investigation
          </button>
        </div>

        {/* Error */}
        {error && (
          <p className="text-red-400 text-xs font-mono mb-4">— Failed to load investigations.</p>
        )}

        {/* Table */}
        <div className="border border-raven-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-raven-800 border-b border-raven-700">
                {['Name', 'Status', 'Files', 'Created', 'Actions'].map((h) => (
                  <th key={h} className="text-left px-4 py-3 text-raven-400 text-xs uppercase tracking-widest font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading && [1, 2, 3].map((i) => <SkeletonRow key={i} />)}

              {!isLoading && data?.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-20">
                    <p className="text-raven-400 text-sm">No investigations.</p>
                    <p className="text-raven-600 text-xs mt-1 font-mono">Upload a log file to begin.</p>
                    <button
                      onClick={() => navigate('/investigations/new')}
                      className="mt-4 border border-electric-500 text-electric-500 text-xs px-4 py-1.5 rounded-none hover:bg-electric-900 transition-colors"
                    >
                      + New Investigation
                    </button>
                  </td>
                </tr>
              )}

              {data?.map((inv) => (
                <tr
                  key={inv.id}
                  className="bg-raven-900 border-t border-raven-700 hover:bg-raven-800 transition-colors"
                >
                  <td className="px-4 py-3 text-raven-200 font-medium text-sm">{inv.name}</td>
                  <td className="px-4 py-3">
                    <Badge value={inv.status} variant="status" />
                  </td>
                  <td className="px-4 py-3 text-raven-400 font-mono text-xs">
                    {inv.files?.length ?? 0}
                  </td>
                  <td className="px-4 py-3 text-raven-400 font-mono text-xs">
                    {new Date(inv.created_at).toLocaleDateString('en-GB')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => navigate(`/investigations/${inv.id}`)}
                        className="text-raven-400 text-xs hover:text-electric-500 transition-colors"
                      >
                        view
                      </button>
                      <span className="text-raven-700">|</span>
                      {inv.status === 'complete' && (
                        <>
                          <button
                            onClick={() => navigate(`/investigations/${inv.id}/report`)}
                            className="text-raven-400 text-xs hover:text-electric-500 transition-colors"
                          >
                            report
                          </button>
                          <span className="text-raven-700">|</span>
                        </>
                      )}
                      <button
                        onClick={() => handleDelete(inv.id)}
                        className="text-raven-400 text-xs hover:text-red-400 transition-colors"
                      >
                        delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  )
}
