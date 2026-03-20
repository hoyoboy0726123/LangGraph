'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { MessageSquare, CalendarClock, FolderOpen, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

const nav = [
  { href: '/chat',  label: '對話',     icon: MessageSquare },
  { href: '/tasks', label: '定時任務', icon: CalendarClock },
  { href: '/files', label: '輸出檔案', icon: FolderOpen },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-60 border-r border-gray-200 flex flex-col bg-white shrink-0">
      {/* Logo */}
      <div className="h-14 flex items-center gap-2.5 px-5 border-b border-gray-200">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
          <Zap className="w-4 h-4 text-white" strokeWidth={2.5} />
        </div>
        <span className="font-semibold text-gray-900 tracking-tight">LangGraph Agent</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150',
              pathname.startsWith(href)
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            )}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <p className="text-xs text-gray-400 text-center">Powered by Groq + LangGraph</p>
      </div>
    </aside>
  )
}
