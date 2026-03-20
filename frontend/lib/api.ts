import type { OutputFormat, StepEvent, ScheduledTask, FileItem } from './types'

const BASE = '/api/backend'

// ── Chat / Run ──────────────────────────────────────────────
export async function* streamTask(
  task: string,
  format: OutputFormat = 'md',
  savePath?: string
): AsyncGenerator<StepEvent> {
  const res = await fetch(`${BASE}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task, output_format: format, save_path: savePath ?? null, stream: true }),
  })

  if (!res.ok) {
    throw new Error(`API 錯誤：${res.status}`)
  }

  const reader = res.body?.getReader()
  if (!reader) throw new Error('無法讀取串流')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    let event = ''
    let data = ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        event = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        data = line.slice(6).trim()
      } else if (line === '' && event && data) {
        try {
          const parsed = JSON.parse(data)
          yield { type: event as StepEvent['type'], ...parsed }
        } catch { /* ignore malformed */ }
        event = ''
        data = ''
      }
    }
  }
}

// ── Tasks ───────────────────────────────────────────────────
export async function getTasks(): Promise<ScheduledTask[]> {
  const res = await fetch(`${BASE}/tasks`)
  const data = await res.json()
  return data.tasks ?? []
}

export async function createTask(task: {
  name: string
  task_prompt: string
  output_format: OutputFormat
  save_path?: string
  schedule_type: string
  schedule_expr: string
}): Promise<ScheduledTask> {
  const res = await fetch(`${BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail ?? 'Create task failed')
  }
  const data = await res.json()
  return data.task
}

export async function deleteTask(id: string): Promise<void> {
  const res = await fetch(`${BASE}/tasks/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Delete task failed')
}

// ── Files ───────────────────────────────────────────────────
export async function listFiles(path = ''): Promise<FileItem[]> {
  const res = await fetch(`${BASE}/files?path=${encodeURIComponent(path)}`)
  const data = await res.json()
  return data.files ?? []
}

export async function readFile(path: string): Promise<{ content: string; name: string }> {
  const res = await fetch(`${BASE}/files/content?path=${encodeURIComponent(path)}`)
  if (!res.ok) throw new Error('Read file failed')
  return res.json()
}

// ── Health ──────────────────────────────────────────────────
export async function getHealth(): Promise<{ status: string; warnings: string[] }> {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}
