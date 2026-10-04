import { proxyJson } from '../proxy';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get('limit') || '50';
  const offset = searchParams.get('offset') || '0';
  const decision = searchParams.get('decision') || '';
  const qs = new URLSearchParams({ limit, offset });
  if (decision) qs.set('decision', decision);
  return proxyJson(`/api/requests?${qs.toString()}`);
}