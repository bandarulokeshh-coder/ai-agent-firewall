import { proxyJson } from '../../../proxy';

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return proxyJson(`/api/tool-call/${id}/reject`, { method: 'POST' });
}
