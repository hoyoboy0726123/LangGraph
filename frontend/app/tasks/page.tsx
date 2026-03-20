'use client'

import { useState, useEffect } from 'react'
import { Plus, Trash2, CalendarClock, Clock, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import type { ScheduledTask, OutputFormat } from '@/lib/types'
import { getTasks, createTask, deleteTask } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'

const FORMAT_OPTS: OutputFormat[] = ['md', 'table', 'json', 'yaml', 'csv']
const SCHEDULE_PRESETS = [
  { label: '每天早上 9 點', type: 'cron', expr: '0 9 * * *' },
  { label: '每週一早上', type: 'cron', expr: '0 9 * * 1' },
  { label: '每 30 分鐘', type: 'interval', expr: '30m' },
  { label: '每小時', type: 'interval', expr: '1h' },
  { label: '每天', type: 'interval', expr: '1d' },
]

export default function TasksPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    task_prompt: '',
    output_format: 'md' as OutputFormat,
    save_path: '',
    schedule_type: 'cron',
    schedule_expr: '0 9 * * *',
  })

  const load = async () => {
    try {
      setLoading(true)
      setTasks(await getTasks())
    } catch {
      toast.error('載入任務失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.name || !form.task_prompt) {
      toast.error('請填寫任務名稱和內容')
      return
    }
    try {
      await createTask({
        ...form,
        save_path: form.save_path || undefined,
      })
      toast.success('任務已建立')
      setShowForm(false)
      setForm({ name: '', task_prompt: '', output_format: 'md', save_path: '', schedule_type: 'cron', schedule_expr: '0 9 * * *' })
      load()
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '建立失敗')
    }
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`確定刪除任務「${name}」？`)) return
    try {
      await deleteTask(id)
      toast.success('任務已刪除')
      setTasks(prev => prev.filter(t => t.id !== id))
    } catch {
      toast.error('刪除失敗')
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-6 border-b border-gray-200 shrink-0">
        <h1 className="text-sm font-medium text-gray-900">定時任務</h1>
        <div className="flex items-center gap-2">
          <button onClick={load} className="btn-ghost text-xs">
            <RefreshCw className="w-3.5 h-3.5" />
            刷新
          </button>
          <button onClick={() => setShowForm(v => !v)} className="btn-primary text-sm py-2 px-4">
            <Plus className="w-4 h-4" />
            新增任務
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">

          {/* Create Form */}
          {showForm && (
            <div className="card p-5 space-y-4 animate-slide-up">
              <h2 className="font-semibold text-gray-900">新增定時任務</h2>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">任務名稱</label>
                  <input
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="input-base text-sm"
                    placeholder="例：每日股市報告"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">輸出格式</label>
                  <select
                    value={form.output_format}
                    onChange={e => setForm(f => ({ ...f, output_format: e.target.value as OutputFormat }))}
                    className="input-base text-sm"
                  >
                    {FORMAT_OPTS.map(o => <option key={o} value={o}>{o.toUpperCase()}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">任務描述</label>
                <textarea
                  value={form.task_prompt}
                  onChange={e => setForm(f => ({ ...f, task_prompt: e.target.value }))}
                  className="input-base text-sm resize-none"
                  rows={3}
                  placeholder="例：爬取台積電 Yahoo 股價，整理今日漲跌資訊"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">排程設定</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {SCHEDULE_PRESETS.map(p => (
                    <button
                      key={p.expr}
                      onClick={() => setForm(f => ({ ...f, schedule_type: p.type, schedule_expr: p.expr }))}
                      className={cn(
                        'text-xs px-3 py-1.5 rounded-lg border transition-colors',
                        form.schedule_expr === p.expr
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-gray-200 text-gray-600 hover:border-gray-300'
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <select
                    value={form.schedule_type}
                    onChange={e => setForm(f => ({ ...f, schedule_type: e.target.value }))}
                    className="input-base text-sm w-32"
                  >
                    <option value="cron">Cron</option>
                    <option value="interval">間隔</option>
                    <option value="once">單次</option>
                  </select>
                  <input
                    value={form.schedule_expr}
                    onChange={e => setForm(f => ({ ...f, schedule_expr: e.target.value }))}
                    className="input-base text-sm flex-1 font-mono"
                    placeholder="Cron: 0 9 * * * | 間隔: 30m | 單次: 2026-03-20 09:00"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">存檔路徑（可選）</label>
                <input
                  value={form.save_path}
                  onChange={e => setForm(f => ({ ...f, save_path: e.target.value }))}
                  className="input-base text-sm font-mono"
                  placeholder="reports/daily_{date}.md"
                />
              </div>

              <div className="flex gap-2 justify-end pt-1">
                <button onClick={() => setShowForm(false)} className="btn-ghost text-sm">取消</button>
                <button onClick={handleCreate} className="btn-primary text-sm">建立任務</button>
              </div>
            </div>
          )}

          {/* Task List */}
          {loading ? (
            <div className="text-center text-gray-400 py-12 text-sm">載入中...</div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-16">
              <CalendarClock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">尚無定時任務</p>
              <p className="text-gray-400 text-xs mt-1">點擊「新增任務」建立你的第一個排程</p>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map(task => (
                <div key={task.id} className="card p-4 flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-900 text-sm truncate">{task.name}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0">
                        {task.output_format.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 truncate mb-2">{task.task_prompt}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {task.schedule_type}: <code className="font-mono">{task.schedule_expr}</code>
                      </span>
                      {task.next_run && (
                        <span>下次：{formatDate(task.next_run)}</span>
                      )}
                      {task.last_run && (
                        <span>上次：{formatDate(task.last_run)}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(task.id, task.name)}
                    className="btn-ghost text-red-400 hover:text-red-600 hover:bg-red-50 p-2"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
