'use client'

import { useState, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import type { ChatMessage, OutputFormat, StepEvent } from '@/lib/types'
import { ChatWindow } from '@/components/chat/ChatWindow'
import { InputBar } from '@/components/chat/InputBar'
import { streamTask } from '@/lib/api'
import { genId } from '@/lib/utils'

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streaming, setStreaming] = useState(false)
  const abortRef = useRef<(() => void) | null>(null)

  const updateMessage = useCallback((id: string, patch: Partial<ChatMessage>) => {
    setMessages(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m))
  }, [])

  const appendStep = useCallback((id: string, step: StepEvent) => {
    setMessages(prev => prev.map(m =>
      m.id === id ? { ...m, steps: [...m.steps, step] } : m
    ))
  }, [])

  const handleSend = useCallback(async (task: string, format: OutputFormat) => {
    // Add user message
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content: task,
      format,
      status: 'done',
      steps: [],
      timestamp: new Date(),
    }

    // Add assistant placeholder
    const assistantId = genId()
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      format,
      status: 'streaming',
      steps: [],
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setStreaming(true)

    let cancelled = false
    abortRef.current = () => { cancelled = true }

    try {
      const gen = streamTask(task, format)

      for await (const event of gen) {
        if (cancelled) break

        switch (event.type) {
          case 'plan':
          case 'thinking':
          case 'tool_call':
          case 'status':
            appendStep(assistantId, event)
            break

          case 'result':
          case 'done':
            if (event.output) {
              updateMessage(assistantId, {
                content: event.output,
                format: (event.format as OutputFormat) ?? format,
                status: 'done',
              })
            }
            break

          case 'error':
            updateMessage(assistantId, {
              content: `❌ 執行失敗：${event.message}`,
              status: 'error',
            })
            toast.error(event.message ?? '執行失敗')
            break
        }
      }

      if (!cancelled) {
        updateMessage(assistantId, { status: 'done' })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '未知錯誤'
      updateMessage(assistantId, {
        content: `❌ ${msg}`,
        status: 'error',
      })
      toast.error(msg)
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }, [updateMessage, appendStep])

  const handleStop = useCallback(() => {
    abortRef.current?.()
    setStreaming(false)
  }, [])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center px-6 border-b border-gray-200 shrink-0">
        <h1 className="text-sm font-medium text-gray-900">對話</h1>
      </div>

      {/* Chat Window */}
      <ChatWindow messages={messages} />

      {/* Input */}
      <InputBar
        onSend={handleSend}
        disabled={streaming}
        onStop={handleStop}
      />
    </div>
  )
}
