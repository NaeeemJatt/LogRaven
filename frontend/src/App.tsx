// LogRaven — Root Application Component
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'

import Login           from './pages/Auth/Login'
import Register        from './pages/Auth/Register'
import Dashboard       from './pages/Dashboard'
import NewInvestigation from './pages/NewInvestigation'
import Investigation   from './pages/Investigation'
import JobStatus       from './pages/JobStatus'
import Report          from './pages/Report'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
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

        {/* Default */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
