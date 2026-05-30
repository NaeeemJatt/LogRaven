// LogRaven — Root Application Component
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AuthBootstrap from './components/layout/AuthBootstrap'
import Navbar from './components/layout/Navbar'

import Login           from './pages/Auth/Login'
import Register        from './pages/Auth/Register'
import Landing         from './pages/Landing'
import Dashboard       from './pages/Dashboard'
import NewInvestigation from './pages/NewInvestigation'
import Investigation   from './pages/Investigation'
import JobStatus       from './pages/JobStatus'
import Report          from './pages/Report'
import PlayParser      from './pages/PlayParser'
import AuditPage       from './pages/AuditPage'
import ProfilePage     from './pages/Profile'
import AlertFeed       from './pages/AlertFeed'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthBootstrap>
        <Routes>
          {/* Public */}
          <Route path="/"         element={<Landing />} />
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected — shell wraps all authenticated pages */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <div className="min-h-screen bg-void">
                  <Navbar />
                  <Routes>
                    <Route path="/dashboard"                      element={<Dashboard />} />
                    <Route path="/investigations/new"             element={<NewInvestigation />} />
                    <Route path="/investigations/:id"             element={<Investigation />} />
                    <Route path="/investigations/:id/status"      element={<JobStatus />} />
                    <Route path="/investigations/:id/report"      element={<Report />} />
                    <Route path="/play-parser"                    element={<PlayParser />} />
                    <Route path="/compliance"                     element={<AuditPage />} />
                    <Route path="/alerts"                         element={<AlertFeed />} />
                    <Route path="/profile"                        element={<ProfilePage />} />
                    <Route path="*"                               element={<Navigate to="/dashboard" replace />} />
                  </Routes>
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthBootstrap>
    </BrowserRouter>
  )
}
