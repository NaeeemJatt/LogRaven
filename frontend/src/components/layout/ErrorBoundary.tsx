// LogRaven — Global error boundary
//
// Catches render-time errors anywhere in the tree so a component crash
// shows a recoverable screen instead of a white page.

import React from 'react'

interface State {
  hasError: boolean
  message: string
}

export default class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(error: unknown): State {
    return { hasError: true, message: error instanceof Error ? error.message : String(error) }
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    console.error('[LogRaven] Uncaught render error:', error, info.componentStack)
  }

  private reset = () => {
    this.setState({ hasError: false, message: '' })
    window.location.href = '/dashboard'
  }

  render() {
    if (!this.state.hasError) return this.props.children

    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-[#030508]">
        <div className="w-full max-w-md text-center">
          <p className="font-mono font-bold tracking-widest text-[#818CF8] text-lg uppercase mb-8">LOGRAVEN</p>
          <h1 className="text-text-primary text-2xl font-semibold mb-3">Something went wrong</h1>
          <p className="text-text-muted text-sm leading-relaxed mb-2">
            The page hit an unexpected error. Your data is safe — try reloading.
          </p>
          {this.state.message && (
            <p className="font-mono text-[11px] text-text-ghost mb-8 break-all">{this.state.message}</p>
          )}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => window.location.reload()}
              className="btn-login text-sm font-medium tracking-wide py-2.5 px-6 rounded transition-colors uppercase cursor-pointer"
            >
              Reload
            </button>
            <button
              onClick={this.reset}
              className="text-sm text-text-muted hover:text-text-primary border border-white/[0.1] py-2.5 px-6 rounded transition-colors cursor-pointer"
            >
              Go to dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }
}
