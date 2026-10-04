import { NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  // Forward the multipart body untouched; never read raw content in Next.js.
  const body = await request.blob();
  const upstream = await fetch(`${API_URL}/api/files/scan`, {
    method: 'POST',
    headers: { 'Content-Type': request.headers.get('Content-Type') || 'application/octet-stream' },
    body,
    cache: 'no-store',
  });
  const text = await upstream.text();
  let data: unknown = {};
  try {
    data = JSON.parse(text);
  } catch {
    return new NextResponse(text, { status: upstream.status });
  }
  return NextResponse.json(data, { status: upstream.status });
}