'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Shield, Send, UploadCloud, RefreshCw, FileText, CheckCircle, AlertTriangle, XCircle, LayoutDashboard, Plus, History, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface ProviderInfo { name: string; default_model: string; configured: boolean }
interface RiskReason { points: number; reason: string }
interface ChatMsg {
  role: 'user' | 'assistant';
  content: string;
  meta?: {
    prompt?: string;
    decision?: string; risk?: number; level?: string;
    reasons?: RiskReason[]; injection?: number; classification?: string;
    pii_count?: number; secret_count?: number;
    sanitized_preview?: string; request_id?: string;
  };
}
interface ChatSession {
  id: string;
  timestamp: number;
  preview: string;
  messageCount: number;
}
interface ScanResult {
  filename: string; extension: string; mime_type: string;
  size_bytes: number; sha256: string; pages?: number;
  pii_count: number; secret_count: number; classification: string;
  risk_score: number; risk_level: string; decision: string;
  pii: { label: string; count: number }[]; secrets: { label: string; count: number }[];
  file_id?: string | null; redactions?: { label: string; count: number }[];
}

const DECISION_STYLE: Record<string, string> = {
  ALLOW: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  WARN: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  REDACT: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  REDACTED: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  APPROVAL: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  BLOCK: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400',
  FAILED: 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-300',
};
const DECISION_ICON: Record<string, any> = {
  ALLOW: CheckCircle, WARN: AlertTriangle, REDACT: AlertTriangle,
  REDACTED: AlertTriangle, APPROVAL: AlertTriangle, BLOCK: XCircle, FAILED: XCircle,
};

// localStorage key for the stable conversation id (chat survives reloads).
const IFW_SESSION_KEY = 'ifw_chat_session';
const IFW_HISTORY_KEY = 'ifw_chat_history';

function ChatGatewayPage() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState('gemma4:e4b');
  const [installedModels, setInstalledModels] = useState<string[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [prompt, setPrompt] = useState('');
  const [busy, setBusy] = useState(false);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<string[]>([]);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);
  const [showSanitized, setShowSanitized] = useState(false);
  const [dashStats, setDashStats] = useState<any>(null);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const reconnectRef = useRef<any>(undefined);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Stable conversation id persisted in localStorage, so the same /chat
  // conversation survives page reloads instead of restarting each time.
  const [sessionId, setSessionId] = useState(() => {
    try {
      const existing = localStorage.getItem(IFW_SESSION_KEY);
      if (existing) return existing;
      const s = `fg-${Date.now()}`;
      localStorage.setItem(IFW_SESSION_KEY, s);
      return s;
    } catch {
      return `fg-${Date.now()}`;
    }
  });

  // Mirror of current messages so submit() can build the full next transcript
  // (for setting state AND persisting) without stale-closure pitfalls.
  const messagesRef = useRef<ChatMsg[]>([]);
  useEffect(() => { messagesRef.current = messages; }, [messages]);

  // Best-effort save of the transcript after every exchange.
  const persist = useCallback(async (next: ChatMsg[]) => {
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, messages: next }),
        cache: 'no-store',
      });
      // Update history after saving
      updateHistory(sessionId, next);
    } catch { /* persistence is best-effort */ }
  }, [sessionId]);

  const updateHistory = useCallback((sid: string, msgs: ChatMsg[]) => {
    if (msgs.length === 0) return;
    try {
      const history: ChatSession[] = JSON.parse(localStorage.getItem(IFW_HISTORY_KEY) || '[]');
      const firstUserMsg = msgs.find(m => m.role === 'user')?.content || 'New conversation';
      const preview = firstUserMsg.slice(0, 60) + (firstUserMsg.length > 60 ? '...' : '');
      const existing = history.findIndex(h => h.id === sid);
      const session: ChatSession = {
        id: sid,
        timestamp: Date.now(),
        preview,
        messageCount: msgs.length,
      };
      if (existing >= 0) {
        history[existing] = session;
      } else {
        history.unshift(session);
      }
      localStorage.setItem(IFW_HISTORY_KEY, JSON.stringify(history.slice(0, 50)));
      setChatHistory(history.slice(0, 50));
    } catch { /* history is best-effort */ }
  }, []);

  const loadHistory = useCallback(() => {
    try {
      const history: ChatSession[] = JSON.parse(localStorage.getItem(IFW_HISTORY_KEY) || '[]');
      setChatHistory(history);
    } catch { /* history is best-effort */ }
  }, []);

  // Restore the saved transcript on first load so the chat doesn't restart.
  useEffect(() => {
    loadHistory();
    (async () => {
      try {
        const res = await fetch(`/api/chat?session_id=${encodeURIComponent(sessionId)}`, { cache: 'no-store' });
        if (!res.ok) return;
        const d = await res.json();
        if (Array.isArray(d.messages) && d.messages.length > 0) {
          const restored = d.messages.map((m: any) => ({ role: m.role, content: m.content, meta: m.meta }));
          setMessages(restored);
          messagesRef.current = restored;
        }
      } catch { /* nothing saved yet */ }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const loadProviders = useCallback(async () => {
    try {
      const res = await fetch('/api/providers');
      if (!res.ok) return;
      const data = await res.json();
      setProviders(Array.isArray(data) ? data : []);
      if (data[0]) {
        setProvider(data[0].name);
        setModel(data[0].default_model || 'gemma4:e4b');
      }
    } catch { /* backend not up yet */ }
  }, []);

  const loadModels = useCallback(async (providerName: string) => {
    try {
      const res = await fetch(`/api/providers/models?provider=${encodeURIComponent(providerName)}`);
      if (!res.ok) return;
      const data = await res.json();
      const models: string[] = Array.isArray(data?.models) ? data.models : [];
      setInstalledModels(models);
      // Default the dropdown to the first installed model if the current one isn't pulled.
      if (models.length > 0) {
        setModel(prev => (models.includes(prev) ? prev : models[0]));
      }
    } catch { /* backend not up yet */ }
  }, []);

  useEffect(() => { loadModels(provider); }, [provider, loadModels]);

  useEffect(() => { loadProviders(); }, [loadProviders]);
  useEffect(() => {
    fetch('/api/dashboard').then(r => r.json()).then(d => setDashStats(d)).catch(() => {});
  }, []);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const connect = () => {
      if (disposed) return;
      const envUrl = process.env.NEXT_PUBLIC_WS_URL;
      const wsUrl = envUrl || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws`;
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setConnected(true);
      ws.onerror = () => ws?.close();
      ws.onclose = () => { setConnected(false); if (!disposed) timer = setTimeout(connect, 3000); };
      ws.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.type === 'ai_request' || d.type === 'file_scan' || d.type === 'approval_request') {
            setLiveEvents(prev => [{ ...d, _t: Date.now() }, ...prev].slice(0, 100));
          }
        } catch { /* ignore */ }
      };
    };
    // Defer the first connect out of React 18 StrictMode's mount->unmount->mount
    // churn in dev, so we never open a socket that gets closed mid-handshake.
    timer = setTimeout(connect, 0);
    return () => { disposed = true; clearTimeout(timer); ws?.close(); };
  }, []);
  const buildPayload = useCallback(() => {
    const attachments: any[] = [];
    if (scan && scan.decision !== 'BLOCK') {
      attachments.push({
        type: 'file_scan',
        filename: scan.filename,
        size: scan.size_bytes,
        sha256: scan.sha256,
        classification: scan.classification,
        decision: scan.decision,
        risk: scan.risk_score,
        reason: `${scan.pii_count} PII + ${scan.secret_count} secrets → ${scan.decision}`,
      });
    }
    return {
      prompt, provider, model, session_id: sessionId,
      attachments,
      // Wire the uploaded file's id to the backend so its /api/ai/chat loop can
      // mark it consumed → the privacy tracker schedules verified auto-deletion
      // after this request uses it. (chat page uploads then connect to /privacy.)
      file_ids: scan && scan.file_id ? [scan.file_id] : [],
    };
  }, [prompt, provider, model, scan, sessionId]);

  const submit = async () => {
    const message = prompt.trim();
    if (!message || busy) return;
    setPrompt('');
    const userMsg: ChatMsg = { role: 'user', content: message };
    const afterUser = messagesRef.current.concat(userMsg);
    setMessages(afterUser);
    messagesRef.current = afterUser;
    setBusy(true);
    const start = performance.now();
    try {
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildPayload()),
        cache: 'no-store',
      });
      const data = await res.json().catch(() => ({}));
      const dur = (performance.now() - start).toFixed(0);
      const meta = {
        prompt: message,
        decision: data.decision,
        risk: data.risk?.score ?? 0,
        level: data.risk?.level ?? (data.decision || 'FAILED'),
        reasons: Array.isArray(data.risk?.reasons) ? data.risk.reasons : [],
        injection: data.inspection?.injection?.score,
        classification: data.inspection?.classification,
        pii_count: data.inspection?.pii?.length ?? data.pii_count ?? (data.inspection?.classification?.match(/\+\d+/)?.[0]?.slice(1) ?? '0'),
        secret_count: data.inspection?.secrets?.length ?? data.secret_count ?? 0,
        sanitized_preview: data.sanitized?.preview ?? data.redacted_preview ?? (data.risk?.reasons?.find((r: { reason?: string }) => r.reason?.includes('redacted'))?.reason ?? ''),
        request_id: data.request_id || data.id,
      };
      const content = meta.decision === 'BLOCK'
        ? "**🔒 Request BLOCKED — never sent to the AI provider.**"
        : meta.decision === 'APPROVAL'
          ? "**⏳ Pending manual approval.** Request queued for the security team."
          : meta.decision?.startsWith('REDACT')
            ? (meta.sanitized_preview || "⚠️ Attachments sanitized; prompt sent with redacted content.")
            : (data.response ?? data.message ?? data.content ?? data.answer ?? JSON.stringify({ data })).toString();
      const assistantMsg: ChatMsg = { role: 'assistant', meta, content };
      const afterAssist = messagesRef.current.concat(assistantMsg);
      setMessages(afterAssist);
      messagesRef.current = afterAssist;
      persist(afterAssist); // persist the conversation so it survives reloads
      setLiveEvents(prev => [{ type: data.status_header || data.decision || 'AI_RESPONSE', decision: data.decision,
        risk_score: data.risk?.score ?? 0, request_id: data.request_id ?? data.id ?? '',
        resolved: dur + 'ms', _t: Date.now() }, ...prev].slice(0, 100));
    } catch (err) {
      setMessages(prev => prev.concat({ role: 'assistant', content: `⚠️ Request failed: ${String(err)}` }));
    } finally { setBusy(false); }
  };
  const handleScan = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
      const res = await fetch('/api/files/scan', { method: 'POST', body: fd, cache: 'no-store' });
      if (!res.ok) { setScan(null); return; }
      const j = await res.json();
      setScan({ filename: file.name, extension: file.name.split('.').pop() || '', mime_type: file.type || 'unknown',
        size_bytes: file.size, sha256: j.sha256 || '', pages: j.pages, pii_count: j.pii_count || 0,
        secret_count: j.secret_count || 0, classification: j.classification || 'unknown',
        risk_score: j.risk_score || 0, risk_level: j.risk_level || 'info',
        decision: j.decision || 'ALLOW',
        pii: (Array.isArray(j.pii) ? j.pii : []).map((p: any) => ({ label: p.label, count: p.count || 0 })),
        secrets: (Array.isArray(j.secrets) ? j.secrets : []).map((s: any) => ({ label: s.label, count: s.count || 0 })),
        file_id: j.file_id || null, redactions: (Array.isArray(j.redactions) ? j.redactions : []).map((r: any) => ({ label: r.label, count: r.count || 0 })) });
      setLiveEvents(prev => [{ type: 'file_scan', filename: file.name, decision: j.decision, risk_score: j.risk_score,
        pii_count: j.pii_count, secret_count: j.secret_count, _t: Date.now() }, ...prev].slice(0, 100));
    } catch { setScan(null); }
  };

  const openFiles = () => fileRef.current?.click();
  const clearFiles = () => { setScan(null); if (fileRef.current) fileRef.current.value = ''; };
  const decision = scan?.decision;

  const startNewChat = () => {
    const newSession = `fg-${Date.now()}`;
    localStorage.setItem(IFW_SESSION_KEY, newSession);
    setSessionId(newSession);
    setMessages([]);
    messagesRef.current = [];
    setScan(null);
    setPrompt('');
    setLiveEvents([]);
    if (fileRef.current) fileRef.current.value = '';
  };

  const loadChat = async (session: ChatSession) => {
    try {
      const res = await fetch(`/api/chat?session_id=${encodeURIComponent(session.id)}`, { cache: 'no-store' });
      if (!res.ok) return;
      const d = await res.json();
      if (Array.isArray(d.messages) && d.messages.length > 0) {
        const restored = d.messages.map((m: any) => ({ role: m.role, content: m.content, meta: m.meta }));
        setMessages(restored);
        messagesRef.current = restored;
        localStorage.setItem(IFW_SESSION_KEY, session.id);
        setSessionId(session.id);
        setShowHistory(false);
      }
    } catch { /* failed to load */ }
  };

  const deleteChat = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const history: ChatSession[] = JSON.parse(localStorage.getItem(IFW_HISTORY_KEY) || '[]');
      const updated = history.filter(h => h.id !== sessionId);
      localStorage.setItem(IFW_HISTORY_KEY, JSON.stringify(updated));
      setChatHistory(updated);
    } catch { /* failed to delete */ }
  };

  return (
    <div className="min-h-screen grid grid-cols-[280px_1fr] sm:grid-cols-[320px_1fr] lg:grid-cols-[380px_1fr]">
      {/* ---- Sidebar ---- */}
      <aside className="border-r bg-muted/40 flex flex-col h-screen overflow-y-auto">
        <div className="p-4 pb-3 space-y-4">
          <div className="hover:bg-muted/60 px-3 py-2 rounded-md">
            <h1 className="text-base font-semibold flex items-center gap-2">
              <Shield className="w-5 h-5" /> AI Data & Agent Gateway
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">Real-time firewall for AI traffic</p>
          </div>

          <div className="rounded-lg border bg-card p-3 space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5 text-xs uppercase tracking-wide">Status</span>
              <span className="flex items-center gap-1.5 text-xs font-medium">
                <span className={cn('inline-block h-2 w-2 rounded-full', connected ? 'bg-green-500' : 'bg-red-500')} />
                {connected ? 'Live' : 'Offline'}
              </span>
            </div>
            <StateCard label="Total agents" value={dashStats?.total_agents ?? '—'} />
            <StateCard label="Total actions" value={dashStats?.total_actions ?? '—'} />
            <StateCard label="Blocked" value={dashStats?.blocked_count ?? '—'} />
            <StateCard label="Pending" value={dashStats?.pending_count ?? '—'} />
            <StateCard label="Security events" value={dashStats?.recent_events?.length ?? '—'} />
          </div>

          <button className="w-full inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-muted/60 transition-colors disabled:opacity-50" disabled={busy} onClick={startNewChat}>
            <Plus className="w-4 h-4" /> New Chat
          </button>
          <button className="w-full inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-muted/60 transition-colors" onClick={() => setShowHistory(!showHistory)}>
            <History className="w-4 h-4" /> History {chatHistory.length > 0 && `(${chatHistory.length})`}
          </button>
          <Link href="/" className="w-full inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-muted/60 transition-colors">
            <LayoutDashboard className="w-4 h-4" /> Dashboard
          </Link>
          <button className="w-full inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm hover:bg-muted/60 transition-colors disabled:opacity-50" disabled={busy} onClick={loadProviders}>
            <RefreshCw className="w-4 h-4" /> Refresh providers
          </button>

          {showHistory && (
            <div className="border rounded-lg bg-card p-2 space-y-1 max-h-[300px] overflow-y-auto">
              {chatHistory.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-4">No chat history yet</div>
              ) : (
                chatHistory.map(session => (
                  <div key={session.id} onClick={() => loadChat(session)}
                    className={cn("flex items-start gap-2 p-2 rounded-md hover:bg-muted/60 cursor-pointer transition-colors group",
                      session.id === sessionId && "bg-muted/80")}>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{session.preview}</div>
                      <div className="text-[10px] text-muted-foreground">
                        {new Date(session.timestamp).toLocaleDateString()} · {session.messageCount} msgs
                      </div>
                    </div>
                    <button onClick={(e) => deleteChat(session.id, e)}
                      className="opacity-0 group-hover:opacity-100 hover:text-red-500 transition-opacity p-1">
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <label className="text-xs text-muted-foreground uppercase tracking-wide">AI Provider</label>
            {providers.length === 0 ? (
              <div className="border rounded-lg p-3 bg-muted/30 text-sm text-muted-foreground h-[72px] flex items-center justify-center">
                Waiting for providers… <RefreshCw className="w-4 h-4 animate-spin ml-2" />
              </div>
            ) : (
              <select value={provider} onChange={e => setProvider(e.target.value)}
                className="w-full cursor-pointer border rounded-lg bg-background p-2.5 text-sm outline-none focus:ring-2 focus:ring-ring">
                {providers.map(p => <option key={p.name} value={p.name}>{p.name} {p.configured ? '' : '(unconfigured)'}</option>)}
              </select>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground uppercase tracking-wide">Model</span>
            </div>
            <select value={model} onChange={e => setModel(e.target.value)}
              className="w-full cursor-pointer border rounded-lg bg-background p-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              disabled={installedModels.length === 0}>
              {installedModels.length === 0 ? (
                <option value={model}>{model}</option>
              ) : installedModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            {installedModels.length > 0 && (
              <p className="text-[11px] text-muted-foreground">{installedModels.length} model{installedModels.length === 1 ? '' : 's'} installed</p>
            )}
            {model && installedModels.length > 0 && !installedModels.includes(model) && (
              <p className="text-[11px] text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3" />

                Missing model — pick one above or run `ollama pull {model}`
              </p>
            )}
          </div>

          <div className="border-t pt-3 mt-1 space-y-2">
            <FileCard filename={scan?.filename} risk={scan?.risk_level} decision={decision} onClick={scan ? clearFiles : openFiles} />
            {scan && <div className="flex flex-wrap gap-1.5">
              {scan.pii.map(p => <Chip key={p.label} label={p.label} count={p.count} color="amber" />)}
              {scan.secrets.map(s => <Chip key={s.label} label={s.label} count={s.count} color="red" />)}
            </div>}
          </div>
        </div>
      </aside>
      <main className="flex flex-col flex-1 min-h-0">
        {/* Hidden OS file picker — opened via fileRef by the attach buttons;
            handleScan scans the picked file and tracks it with the backend. */}
        <input type="file" ref={fileRef} onChange={handleScan} className="hidden"
          accept=".pdf,.txt,.docx,.csv,.json,.png,.jpg,.jpeg,.md,.py,.js,.ts,.html,.env"
          title="Attach a document" />
        {/* ---- Live activity panel ---- */}
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          <div className="px-4 py-2 border-b flex items-center justify-between text-xs text-muted-foreground">
            <span className="uppercase tracking-wide font-medium">Live activity</span>
            {liveEvents.length > 0 && <button className="text-muted-foreground hover:text-foreground">Clear</button>}
          </div>
          <div className="flex-1 overflow-y-auto space-y-1 p-3">
            {liveEvents.length === 0 && <div className="text-muted-foreground text-xs text-center py-6 opacity-50">Waiting for gateway events…</div>}
            {liveEvents.map(ev => {
              const Icon = DECISION_ICON[ev.decision] || FileText;
              return (<div key={ev._t} className="text-xs border-b last:border-0 pb-2">
                <div className="flex items-start gap-2">
                  <Icon className="w-3.5 h-3.5 mt-0.5 shrink-0 opacity-70" />
                  <div className="flex-1 min-w-0">
                    <div className="text-muted-foreground text-[10px] uppercase tracking-wide">{ev.type}</div>
                    <div className="text-[12px] truncate">{ev.filename || ev.label || ev.request_id || ev.decision || ''}
                      <span className="ml-1 text-muted-foreground/60">· {ev.resolved ? ev.resolved : new Date(ev._t).toLocaleTimeString()}</span>
                    </div>
                  </div>
                  {ev.decision && <span className={cn('shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium', DECISION_STYLE[ev.decision] || '')}>{ev.decision}</span>}
                </div>
              </div>);
            })}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground select-none">
              <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-4 shadow-sm">
                <Shield className="w-7 h-7 opacity-60" />
              </div>
              <h2 className="text-lg font-medium">AI Gateway Chat</h2>
              <p className="text-sm mt-1 max-w-sm">Type a prompt and hit send. The gateway inspects it for
                PII, secrets, and prompt injection before forwarding to the AI provider.</p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['Send a prompt →', 'Attach a file', 'See live decisions'].map(t =>
                  <span key={t} className="text-xs bg-muted px-3 py-1.5 rounded-md">{t}</span>)}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={cn("flex flex-col gap-1", m.role === 'user' ? 'items-end' : 'items-start')}>
              {m.role === 'assistant' && m.meta && (
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  {m.meta.decision && (<span className={cn('text-[11px] px-2 py-0.5 rounded-full font-medium', DECISION_STYLE[m.meta.decision] || '')}
                    title={`Decision: ${m.meta.decision}`}>{m.meta.decision}</span>)}
                  {m.meta.level && m.meta.decision !== m.meta.level && <span className="text-[11px] text-muted-foreground">{m.meta.level}</span>}
                  {m.meta.risk != null && <span className="text-[11px] text-muted-foreground">Risk {m.meta.risk}</span>}
                  {m.meta.classification && <span className="text-[11px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">{m.meta.classification}</span>}
                </div>
              )}
              <div className={cn("max-w-xl w-full rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap break-words",
                m.role === 'user'
                  ? 'bg-primary text-primary-foreground align-self-end rounded-br-none'
                  : 'bg-card border shadow-sm align-self-start rounded-bl-none')}>
                <p className="text-sm">{m.content}</p>
                {m.role === 'assistant' && m.meta && (
                  <div className="mt-3 border-t pt-2 text-[11px] text-muted-foreground space-y-1 max-w-sm">
                    {m.meta.injection != null && <div className="flex items-center gap-1"><span className={m.meta.injection > 0 ? 'text-rose-500' : 'text-green-500'}>{m.meta.injection > 0 ? '⚠️' : '✓'}</span> Injection score: <span className={cn('font-mono', m.meta.injection > 0 ? 'text-rose-500' : 'text-green-600 dark:text-green-400')}>{m.meta.injection}</span></div>}
                    {m.meta.pii_count != null && <div className="flex items-center gap-1"><span className={m.meta.pii_count > 0 ? 'text-amber-500' : 'text-green-500'}>{m.meta.pii_count > 0 ? '🔍' : '✓'}</span> PII records: <span className={cn('font-mono', m.meta.pii_count > 0 ? 'text-amber-500' : 'text-green-600 dark:text-green-400')}>{m.meta.pii_count}</span></div>}
                    {m.meta.secret_count != null && <div className="flex items-center gap-1"><span className={m.meta.secret_count > 0 ? 'text-rose-500' : 'text-green-500'}>{m.meta.secret_count > 0 ? '🔑' : '✓'}</span> Secrets: <span className={cn('font-mono', m.meta.secret_count > 0 ? 'text-rose-500' : 'text-green-600 dark:text-green-400')}>{m.meta.secret_count}</span></div>}
                    {m.meta.reasons?.length ? (
                      <>
                        <div className="font-medium text-[11px] not-italic text-foreground mt-1">Why {m.meta.decision}?</div>
                        {m.meta.reasons.map((r, ri) => <div key={ri} className="flex items-start gap-1.5">
                          <span className="font-mono text-muted-foreground/80 shrink-0">+{r.points}</span>
                          <span>{r.reason}</span>
                        </div>)}
                      </>
                    ) : null}
                    {m.meta.request_id && <div className="mt-1.5 text-[10px] opacity-60 font-mono">{m.meta.request_id}</div>}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <RefreshCw className="w-4 h-4 animate-spin" /> Inspecting prompt &amp; attachments…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        {/* Input bar */}
        <div className="p-4 border-t bg-card/80">
          <div className="flex items-end gap-3 max-w-3xl">
            <div className="flex-1 flex flex-col gap-2">
              <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
                placeholder="Send a prompt to the AI provider…" className="w-full min-h-[80px] max-h-[240px] resize-none rounded-xl border bg-background p-3 text-sm outline-none focus:ring-2 focus:ring-ring placeholder:text-muted-foreground"
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
                disabled={busy} rows={2} />
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Supports {providers.length} providers · pii/secrets/injection scan</span>
                {prompt && <span className="font-mono">{prompt.length} chars</span>}
              </div>
            </div>
            <button disabled={busy} onClick={openFiles} className="shrink-0" title="Attach a file">
              <UploadCloud className={cn('w-5 h-5 text-muted-foreground hover:text-foreground', busy && 'animate-pulse')} />
            </button>
            <button disabled={busy || !prompt.trim()} onClick={submit} className="shrink-0 bg-primary hover:bg-primary/90 disabled:opacity-40 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2">
              <Send className="w-4 h-4" /> Send
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

function StateCard({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between">
    <span className="text-muted-foreground text-xs">{label}</span>
    <span className="text-xs font-mono">{value}</span>
  </div>;
}

function Chip({ label, count, color }: { label: string; count: number; color: 'amber' | 'red' }) {
  return (<span className={cn("text-[10px] px-2 py-0.5 rounded font-medium border",
    color === 'red' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800')}>
    {label} ×{count}</span>);
}

function FileCard({ filename, risk, decision, onClick }: { filename?: string; risk?: string; decision?: string; onClick?: () => void }) {
  const Icon = decision ? DECISION_ICON[decision] : null;
  if (!filename) return (<button onClick={onClick} className="w-full border rounded-lg p-2.5 text-sm text-muted-foreground hover:bg-muted/60 transition-colors flex items-center gap-2" title="Attach a file">
    <UploadCloud className="w-4 h-4" /> Attach file…</button>);
  return <button onClick={onClick} title="Clear attached file" className="w-full flex items-center gap-2 rounded-lg border bg-muted/40 hover:bg-muted/60 transition-colors px-3 py-2 text-sm group">
    <FileText className={cn('w-4 h-4', decision && DECISION_STYLE[decision] ? 'text-' + risk : 'text-muted-foreground')} />
    <div className="flex-1 min-w-0">
      <div className="truncate font-medium text-foreground text-xs">{filename}</div>
      {decision && <div className="text-[10px] text-muted-foreground flex items-center gap-1">{Icon && <Icon className="w-3 h-3 shrink-0" />} Decision: <span className={cn('font-medium', DECISION_STYLE[decision] || '')}>{decision}</span>{', Risk: ' + (risk ?? '—')}</div>}
    </div>
  </button>;
}

export default ChatGatewayPage;