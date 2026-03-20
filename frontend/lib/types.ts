export type OutputFormat = 'md' | 'table' | 'json' | 'yaml' | 'csv'

export type MessageRole = 'user' | 'assistant'

export type MessageStatus = 'pending' | 'streaming' | 'done' | 'error'

export interface StepEvent {
  type: 'plan' | 'thinking' | 'tool_call' | 'status' | 'result' | 'done' | 'error'
  message?: string
  plan?: string[]
  tool?: string
  args?: string
  output?: string
  format?: OutputFormat
  step?: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  format: OutputFormat
  status: MessageStatus
  steps: StepEvent[]
  timestamp: Date
}

export interface ScheduledTask {
  id: string
  name: string
  task_prompt: string
  output_format: OutputFormat
  save_path: string | null
  schedule_type: 'cron' | 'interval' | 'once'
  schedule_expr: string
  next_run: string | null
  last_run: string | null
  enabled: boolean
}

export interface FileItem {
  name: string
  path: string
  is_dir: boolean
  size: number
  modified: string
}
