/**
 * Next.js API Route：代理聊天請求到 Python FastAPI（支援 SSE 串流）
 */
export async function POST(req: Request) {
  const body = await req.json()

  const upstream = await fetch('http://localhost:8000/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!upstream.ok) {
    return new Response(
      JSON.stringify({ error: `Backend error: ${upstream.status}` }),
      { status: upstream.status, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // SSE 串流直接 pass-through
  return new Response(upstream.body, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
