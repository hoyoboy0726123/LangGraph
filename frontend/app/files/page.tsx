'use client'

import { useState, useEffect } from 'react'
import { Folder, FileText, ArrowLeft, RefreshCw, Eye } from 'lucide-react'
import { toast } from 'sonner'
import type { FileItem } from '@/lib/types'
import { listFiles, readFile } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'
import { OutputRenderer } from '@/components/output/OutputRenderer'

function getFormat(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase() ?? ''
  const map: Record<string, string> = { md: 'md', json: 'json', yaml: 'yaml', yml: 'yaml', csv: 'csv' }
  return (map[ext] ?? 'md') as any
}

export default function FilesPage() {
  const [currentPath, setCurrentPath] = useState('')
  const [files, setFiles] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<{ name: string; content: string; format: string } | null>(null)

  const load = async (path: string) => {
    try {
      setLoading(true)
      const items = await listFiles(path)
      setFiles(items)
      setCurrentPath(path)
    } catch {
      toast.error('載入失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load('') }, [])

  const handleOpen = async (item: FileItem) => {
    if (item.is_dir) {
      load(item.path)
    } else {
      try {
        const { content, name } = await readFile(item.path)
        setPreview({ name, content, format: getFormat(name) })
      } catch {
        toast.error('無法讀取檔案')
      }
    }
  }

  const goUp = () => {
    const parts = currentPath.split('/').filter(Boolean)
    parts.pop()
    load(parts.join('/'))
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-6 border-b border-gray-200 shrink-0">
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-medium text-gray-900">輸出檔案</h1>
          {currentPath && (
            <span className="text-xs text-gray-400 font-mono">/ {currentPath}</span>
          )}
        </div>
        <div className="flex gap-2">
          {currentPath && (
            <button onClick={goUp} className="btn-ghost text-xs">
              <ArrowLeft className="w-3.5 h-3.5" />
              上層
            </button>
          )}
          <button onClick={() => load(currentPath)} className="btn-ghost text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            刷新
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File List */}
        <div className={`${preview ? 'w-72 border-r border-gray-200' : 'flex-1'} overflow-y-auto p-4`}>
          {loading ? (
            <div className="text-center text-gray-400 py-12 text-sm">載入中...</div>
          ) : files.length === 0 ? (
            <div className="text-center py-16">
              <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">此目錄為空</p>
            </div>
          ) : (
            <div className="space-y-0.5">
              {files.map(file => (
                <button
                  key={file.path}
                  onClick={() => handleOpen(file)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
                             hover:bg-gray-50 transition-colors text-left group"
                >
                  {file.is_dir ? (
                    <Folder className="w-5 h-5 text-amber-400 shrink-0" />
                  ) : (
                    <FileText className="w-5 h-5 text-gray-400 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate font-medium">{file.name}</p>
                    {!file.is_dir && (
                      <p className="text-xs text-gray-400">
                        {formatBytes(file.size)} · {formatDate(file.modified)}
                      </p>
                    )}
                  </div>
                  {!file.is_dir && (
                    <Eye className="w-4 h-4 text-gray-300 opacity-0 group-hover:opacity-100 shrink-0" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Preview Panel */}
        {preview && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="h-10 flex items-center justify-between px-4 border-b border-gray-200 bg-gray-50 shrink-0">
              <span className="text-xs font-medium text-gray-600 font-mono">{preview.name}</span>
              <button onClick={() => setPreview(null)} className="btn-ghost text-xs py-1 px-2">關閉</button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <OutputRenderer content={preview.content} format={preview.format as any} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
