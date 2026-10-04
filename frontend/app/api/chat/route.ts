import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '../proxy';

// GET /api/chat?session_id=X        → restore a saved transcript
// POST /api/chat {session_id, messages} → persist the current transcript
export async function GET(request: NextRequest) {
  const sid = request.nextUrl.searchParams.get('session_id') || '';
  return proxyJson(`/api/chat/history?session_id=${encodeURIComponent(sid)}`);
}

export async function POST(request: NextRequest) {
  let body: any = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  if (!body?.session_id || !Array.isArray(body.messages)) {
    return NextResponse.json({ error: 'session_id and messages are required' }, { status: 400 });
  }
  return proxyJson('/api/chat/save', {
    method: 'POST',
    body: JSON.stringify({ session_id: body.session_id, messages: body.messages }),
  });
}