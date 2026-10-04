import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function proxyJson(path: string, init?: RequestInit) {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
      cache: 'no-store',
    });
  } catch (error) {
    console.error(`Proxy to ${path} failed: backend unreachable`, error);
    return NextResponse.json({ error: 'Backend unreachable' }, { status: 502 });
  }
  const text = await response.text();
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // Backend returned non-JSON (e.g. plain-text error page) — forward as text.
      return new NextResponse(text, {
        status: response.status,
        headers: { 'Content-Type': response.headers.get('Content-Type') || 'text/plain' },
      });
    }
  }
  return NextResponse.json(data, { status: response.status });
}
