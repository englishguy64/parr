import { Injectable, inject, signal } from '@angular/core';
import { A2uiRendererService } from '@a2ui/angular/v0_9';

export type Mode = 'response' | 'stream';

export interface PayloadEntry {
  surfaceId: string;
  mode: Mode;
  /** Which A2UI message this is: createSurface, updateComponents or updateDataModel. */
  kind: string;
  json: string;
}

/**
 * Talks to the C# Backend API and hands every A2UI message it returns to the A2UI renderer.
 *
 *   response  one JSON array holding all the messages
 *   stream    newline delimited JSON: one A2UI message per line, rendered as each line arrives
 *             (the Backend API translated the agent's AG-UI events into these)
 */
@Injectable({ providedIn: 'root' })
export class AgentService {
  private readonly renderer = inject(A2uiRendererService);
  private readonly apiBase = fetch('config.json')
    .then((r) => r.json())
    .then((c) => (c.apiBase as string).replace(/\/$/, ''))
    .catch(() => 'http://localhost:5200');

  private counter = 0;

  /** Surfaces on screen, oldest first. Each question gets its own surface. */
  readonly surfaceIds = signal<string[]>([]);
  /** Every A2UI message received, so the page can show the payload. */
  readonly payload = signal<PayloadEntry[]>([]);
  readonly busy = signal(false);
  readonly error = signal('');

  async ask(mode: Mode, prompt: string): Promise<void> {
    if (!prompt.trim() || this.busy()) return;
    this.busy.set(true);
    this.error.set('');
    const surfaceId = `${mode}-${++this.counter}`;
    try {
      const base = await this.apiBase;
      const res = await fetch(`${base}/api/a2ui/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, surfaceId }),
      });
      if (!res.ok) throw new Error(`The backend answered ${res.status}`);

      if (mode === 'response') {
        // One complete answer: an array of A2UI messages.
        for (const message of (await res.json()) as Record<string, unknown>[]) {
          await this.apply(message, surfaceId, mode);
        }
      } else {
        // A streamed answer: read the body as it arrives and render each line straight away.
        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let newline: number;
          while ((newline = buffer.indexOf('\n')) >= 0) {
            const line = buffer.slice(0, newline).trim();
            buffer = buffer.slice(newline + 1);
            if (line) await this.apply(JSON.parse(line), surfaceId, mode);
          }
        }
        if (buffer.trim()) await this.apply(JSON.parse(buffer), surfaceId, mode);
      }
    } catch (e) {
      this.error.set(e instanceof Error ? e.message : String(e));
    } finally {
      this.busy.set(false);
    }
  }

  private async apply(message: Record<string, unknown>, surfaceId: string, mode: Mode): Promise<void> {
    const kind = Object.keys(message).find((k) => k !== 'version') ?? 'unknown';
    this.payload.update((p) => [...p, { surfaceId, mode, kind, json: JSON.stringify(message, null, 2) }]);
    if (kind === 'createSurface') this.surfaceIds.update((ids) => [...ids, surfaceId]);
    // The renderer turns the message into components and data on the surface.
    await this.renderer.processMessagesAsync(message);
  }

  clear(): void {
    this.surfaceIds().forEach((id) =>
      this.renderer.processMessages({ version: 'v0.9', deleteSurface: { surfaceId: id } }),
    );
    this.surfaceIds.set([]);
    this.payload.set([]);
  }
}
