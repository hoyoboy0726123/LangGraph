import type { Metadata } from 'next'
import './globals.css'
import { Sidebar } from '@/components/layout/Sidebar'
import { Toaster } from 'sonner'

export const metadata: Metadata = {
  title: 'LangGraph Agent',
  description: 'AI Agent powered by LangGraph + Groq',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-TW">
      <body>
        <div className="flex h-screen overflow-hidden bg-white">
          <Sidebar />
          <main className="flex-1 overflow-hidden flex flex-col min-w-0">
            {children}
          </main>
        </div>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  )
}
