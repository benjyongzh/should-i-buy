export interface StreamEvent {
  type: string
  data: unknown
}

export async function streamEvents(
  path: string,
  body: unknown,
  receive: (event: StreamEvent) => void,
  signal?: AbortSignal,
) {
  const response = await fetch('/api' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) {
    const payload = await response.json()
    throw new Error(
      typeof payload.detail === 'string'
        ? payload.detail
        : payload.detail?.message || 'Conversation request failed',
    )
  }
  if (!response.body) throw new Error('Streaming response is unavailable')
  const reader = response.body.getReader(),
    decoder = new TextDecoder()
  let buffer = '',
    size = 0,
    complete = false
  try {
    while (true) {
      const next = await reader.read()
      if (next.done) break
      size += next.value.length
      if (size > 2_000_000) throw new Error('Conversation stream exceeded its limit')
      buffer += decoder.decode(next.value, { stream: true })
      let match: RegExpExecArray | null
      while ((match = /\r?\n\r?\n/.exec(buffer))) {
        const block = buffer.slice(0, match.index)
        buffer = buffer.slice(match.index + match[0].length)
        const lines = block.split(/\r?\n/)
        const type =
          lines
            .find((line) => line.startsWith('event:'))
            ?.slice(6)
            .trim() || 'message'
        const data = lines
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trimStart())
          .join('\n')
        if (!data) continue
        const value = JSON.parse(data)
        receive({ type, data: value })
        if (type === 'error') throw new Error(value.message || 'Conversation failed')
        if (type === 'complete') complete = true
      }
    }
    if (!complete)
      throw new Error(
        'Connection ended before a validated reply. Partial text cannot change the strategy.',
      )
  } finally {
    await reader.cancel()
    reader.releaseLock()
  }
}
