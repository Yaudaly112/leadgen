/**
 * API client utility.
 *
 * In development, Next.js rewrites proxy /api/* → localhost:8000.
 * In production on Railway, the backend runs on a separate service,
 * so NEXT_PUBLIC_API_URL points to the backend URL.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

export async function apiFetch<T = any>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json();
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
