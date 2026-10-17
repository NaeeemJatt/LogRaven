// LogRaven — Root Application Component
import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AuthBootstrap from './components/layout/AuthBootstrap'
import ErrorBoundary from './components/layout/ErrorBoundary'
import RequireAuth from './components/layout/RequireAuth'
import Navbar from './components/layout/Navbar'

// Public entry pages stay eager for the fastest first paint.
import Login           from './pages/Auth/Login'
import Register        from './pages/Auth/Register'
import ForgotPassword  from './pages/Auth/ForgotPassword'
import ResetPassword   from './pages/Auth/ResetPassword'
import VerifyEmail     from './pages/Auth/VerifyEmail'
import Landing         from './pages/Landing'
import NotFound        from './pages/NotFound'

// Authenticated/heavy pages are route-split so the entry chunk stays small.
const Dashboard        = lazy(() => import('./pages/Dashboard'))
const NewInvestigation = lazy(() => import('./pages/NewInvestigation'))
const Investigation    = lazy(() => import('./pages/Investigation'))
const JobStatus        = lazy(() => import('./pages/JobStatus'))
const Report           = lazy(() => import('./pages/Report'))
const PlayParser       = lazy(() => import('./pages/PlayParser'))
const AuditPage        = lazy(() => import('./pages/AuditPage'))
const ProfilePage      = lazy(() => import('./pages/Profile'))
const AlertFeed        = lazy(() => import('./pages/AlertFeed'))
const SharedAudit      = lazy(() => import('./pages/SharedAudit'))
const AuditorPortalPage = lazy(() => import('./pages/AuditorPortalPage'))
const PrivacyPage      = lazy(() => import('./pages/Legal').then((m) => ({ default: m.PrivacyPage })))
const TermsPage        = lazy(() => import('./pages/Legal').then((m) => ({ default: m.TermsPage })))

function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-void" role="status" aria-label="Loading page">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-ember border-t-transparent" />
    </div>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthBootstrap>
          <Suspense fallback={<RouteFallback />}>
            <Routes>
              {/* Public */}
              <Route path="/"                element={<Landing />} />
              <Route path="/login"           element={<Login />} />
              <Route path="/register"        element={<Register />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password"  element={<ResetPassword />} />
              <Route path="/verify-email"    element={<VerifyEmail />} />
              <Route path="/shared/audit/:token" element={<SharedAudit />} />
              <Route path="/auditor/portal/:token" element={<AuditorPortalPage />} />
              <Route path="/privacy"         element={<PrivacyPage />} />
              <Route path="/terms"           element={<TermsPage />} />

              {/* Protected — shell wraps all authenticated pages */}
              <Route
                path="/*"
                element={
                  <RequireAuth>
                    <div className="min-h-screen bg-void">
                      <Navbar />
                      <Suspense fallback={<RouteFallback />}>
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
                          <Route path="*"                               element={<NotFound />} />
                        </Routes>
                      </Suspense>
                    </div>
                  </RequireAuth>
                }
              />
            </Routes>
          </Suspense>
        </AuthBootstrap>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
