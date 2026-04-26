import type { Actor, SSEEvent } from "./types";

export const TMDB_IMG = "https://image.tmdb.org/t/p";

export function tmdbProfile(path: string | null, size: "w185" | "w342" | "h632" = "w185"): string | null {
  return path ? `${TMDB_IMG}/${size}${path}` : null;
}

export function tmdbPoster(path: string | null, size: "w154" | "w185" | "w342" = "w185"): string | null {
  return path ? `${TMDB_IMG}/${size}${path}` : null;
}

export async function searchActors(query: string, signal?: AbortSignal): Promise<Actor[]> {
  if (!query.trim()) return [];
  const url = `/api/search?q=${encodeURIComponent(query)}&limit=8`;
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  const data = await res.json();
  return data.results;
}

export interface ConnectStreamHandlers {
  onEvent: (event: SSEEvent) => void;
  onClose?: () => void;
  onError?: (err: Error) => void;
}

export function streamConnect(
  aId: number,
  bId: number,
  maxDepth: number,
  handlers: ConnectStreamHandlers,
): () => void {
  const url = `/api/connect/stream?a_id=${aId}&b_id=${bId}&max_depth=${maxDepth}`;
  const es = new EventSource(url);

  es.onmessage = (ev) => {
    try {
      const parsed = JSON.parse(ev.data) as SSEEvent;
      handlers.onEvent(parsed);
      if (parsed.type === "result" || parsed.type === "no_path" || parsed.type === "error") {
        es.close();
        handlers.onClose?.();
      }
    } catch (e) {
      handlers.onError?.(e as Error);
    }
  };

  es.onerror = () => {
    handlers.onError?.(new Error("Connection lost"));
    es.close();
    handlers.onClose?.();
  };

  return () => es.close();
}
