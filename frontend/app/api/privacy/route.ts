import { NextRequest, NextResponse } from 'next/server';
import { proxyJson } from '../proxy';

export async function GET() {
  return proxyJson('/api/privacy');
}

// POST actions: set retention policy, manually delete+verify a file, or force a sweep.
export async function POST(request: NextRequest) {
  let body: any = {};
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const action = body.action;
  if (action === 'policy' && body.policy) {
    return proxyJson('/api/privacy/policy', {
      method: 'POST',
      body: JSON.stringify({ policy: body.policy }),
    });
  }
  if (action === 'delete' && body.fid) {
    return proxyJson(`/api/privacy/files/${encodeURIComponent(body.fid)}/delete`, {
      method: 'POST',
    });
  }
  if (action === 'sweep') {
    return proxyJson('/api/privacy/sweep', { method: 'POST' });
  }
  return NextResponse.json({ error: 'Unknown privacy action' }, { status: 400 });
}