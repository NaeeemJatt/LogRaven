// LogRaven — Page Wrapper
// Wraps page content with consistent padding and max-width.
// TODO Month 1 Week 3: Implement.

export default function PageWrapper({ children }: { children: React.ReactNode }) {
  return <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
}
