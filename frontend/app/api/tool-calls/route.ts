import { proxyJson } from '../proxy';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = searchParams.get('limit') || '50';
  const offset = searchParams.get('offset') || '0';
  return proxyJson(`/api/tool-calls?limit=${limit}&offset=${offset}`);
}
