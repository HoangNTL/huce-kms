import { createParser, type EventSourceMessage } from "eventsource-parser"

export interface ChatStreamCallbacks {
  onToken?: (token: string) => void
  onCitation?: (citation: unknown) => void
  onDone?: () => void
  onError?: (error: Error) => void
}

/**
 * Utility function to consume and parse Server-Sent Events (SSE) stream
 * safely without breaking UTF-8 characters across chunks.
 */
export async function consumeChatStream(
  response: Response,
  callbacks: ChatStreamCallbacks
): Promise<void> {
  if (!response.body) {
    throw new Error("Response body is null or undefined")
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder("utf-8")

  const parser = createParser({
    onEvent: (event: EventSourceMessage) => {
      if (event.data === "[DONE]") {
        callbacks.onDone?.()
        return
      }
      try {
        const parsed = JSON.parse(event.data)
        if (parsed.token) {
          callbacks.onToken?.(parsed.token)
        } else if (parsed.content) {
          callbacks.onToken?.(parsed.content)
        }
        if (parsed.citation) {
          callbacks.onCitation?.(parsed.citation)
        }
      } catch {
        // Plain text token fallback
        callbacks.onToken?.(event.data)
      }
    },
  })

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        callbacks.onDone?.()
        break
      }
      parser.feed(decoder.decode(value, { stream: true }))
    }
  } catch (error) {
    callbacks.onError?.(error instanceof Error ? error : new Error(String(error)))
  } finally {
    reader.releaseLock()
  }
}
