// LogRaven — Navigation Bar
// Shows LogRaven logo, main nav links, user menu.
// Unauthenticated: Login + Get LogRaven buttons
// Authenticated: Dashboard | New Investigation | user menu (logout)
// TODO Month 1 Week 3: Implement.

export default function Navbar() {
  return (
    <nav className="bg-gray-900 text-white px-6 py-4 flex justify-between items-center">
      <span className="text-blue-400 font-bold text-xl">LogRaven</span>
      <span className="text-gray-400 text-sm">Watch your logs. Find the threat.</span>
    </nav>
  )
}
