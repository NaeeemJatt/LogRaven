// LogRaven — Root Application Component
// Sets up React Router with all LogRaven routes.
// Protected routes require authentication (JWT in authStore).
//
// ROUTES:
//   /              — Landing page (public)
//   /login         — Login page (public)
//   /register      — Register page (public)
//   /dashboard     — Investigation list (protected)
//   /new           — Create investigation (protected)
//   /investigation/:id  — Investigation detail + file upload (protected)
//   /status/:id    — Job status polling page (protected)
//   /report/:id    — Full LogRaven report view (protected)
//
// TODO Month 1 Week 3: Implement this file.

import React from 'react'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <h1 className="text-3xl font-bold text-center pt-20 text-blue-600">
        LogRaven
      </h1>
      <p className="text-center text-gray-500 mt-2">
        Watch your logs. Find the threat.
      </p>
      <p className="text-center text-gray-400 mt-4 text-sm">
        Frontend scaffold ready. Implement App.tsx in Month 1 Week 3.
      </p>
    </div>
  )
}
