// LogRaven — Root Application Component
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import AuthBootstrap from './components/layout/AuthBootstrap'

import Login           from './pages/Auth/Login'
import Register        from './pages/Auth/Register'
import Landing         from './pages/Landing'
import Dashboard       from './pages/Dashboard'
import NewInvestigation from './pages/NewInvestigation'
import Investigation   from './pages/Investigation'
import JobStatus       from './pages/JobStatus'
import Report          from './pages/Report'
import PlayParser      from './pages/PlayParser'

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

        {/* Protected */}
        <Route path="/dashboard" element={
          <ProtectedRoute><Dashboard /></ProtectedRoute>
        } />
        <Route path="/investigations/new" element={
          <ProtectedRoute><NewInvestigation /></ProtectedRoute>
        } />
        <Route path="/investigations/:id" element={
          <ProtectedRoute><Investigation /></ProtectedRoute>
        } />
        <Route path="/investigations/:id/status" element={
          <ProtectedRoute><JobStatus /></ProtectedRoute>
        } />
        <Route path="/investigations/:id/report" element={
          <ProtectedRoute><Report /></ProtectedRoute>
        } />
        <Route path="/play-parser" element={
          <ProtectedRoute><PlayParser /></ProtectedRoute>
        } />

        {/* Unknown paths → home (marketing); authenticated users use /dashboard from UI */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </AuthBootstrap>
    </BrowserRouter>
  )
}
