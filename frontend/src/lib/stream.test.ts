import { afterEach, expect, it, vi } from 'vitest'
import { streamEvents } from './stream'

afterEach(() => vi.unstubAllGlobals())

it('delivers incremental SSE events across UTF8 and CRLF chunk boundaries', async () => {
  const text =
    'event: delta\r\ndata: {"text":"Hi 😊"}\r\n\r\nevent: complete\r\ndata: {"ok":true}\r\n\r\n'
  const bytes = new TextEncoder().encode(text)
  const stream = new ReadableStream({
    start(controller) {
      for (const byte of bytes) controller.enqueue(new Uint8Array([byte]))
      controller.close()
    },
  })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream)))
  const events: unknown[] = []
  await streamEvents('/fixture', {}, (event) => events.push(event))
  expect(events).toEqual([
    { type: 'delta', data: { text: 'Hi 😊' } },
    { type: 'complete', data: { ok: true } },
  ])
})

it('rejects a dropped connection after partial text instead of reporting completion', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('event: delta\ndata: {"text":"partial"}\n\n')),
  )
  const receive = vi.fn()
  await expect(streamEvents('/fixture', {}, receive)).rejects.toThrow('before a validated reply')
  expect(receive).toHaveBeenCalledWith({ type: 'delta', data: { text: 'partial' } })
})

it('surfaces server error events and HTTP conflicts without accepting text', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce(
        new Response('event: error\ndata: {"message":"validation failed"}\n\n'),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'stale draft' }), { status: 409 }),
      ),
  )
  await expect(streamEvents('/fixture', {}, vi.fn())).rejects.toThrow('validation failed')
  await expect(streamEvents('/fixture', {}, vi.fn())).rejects.toThrow('stale draft')
})
