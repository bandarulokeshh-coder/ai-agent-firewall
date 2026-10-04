'use client';

import { useState, useEffect, useCallback } from 'react';
import { Shield, Trash2, RefreshCw, FileText, CheckCircle, Clock, AlertTriangle, LayoutDashboard } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface PrivacyFile {
  fid: string;
  filename: string;
  extension: string;
  size_bytes: number;
  classification: string;
  risk_score: number;
  risk_level: string;
  state: 'ACTIVE' | 'PENDING' | 'DELETED';
  consumed_at?: string | null;
  deleted_at?: string | null;
  deleted_by?: string | null;
  verified?: boolean | null;
  verification_at?: string | null;
}

interface Activity {
  ts?: string;
  event: string;
  fid?: string;
  filename?: string;
  detail?: string;
}

interface Stats {
  total_uploads: number;
  consumed: number;
  active: number;
  pending: number;
  deleted: number;
  deleted_verified: number;
  delete_failed: number;
  manual_deletes: number;
}

interface PolicyOpt { key: string; label: string }

const STATE_STYLE: Record<string, { badge: string; dot: string }> = {
  ACTIVE: { badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400', dot: 'bg-emerald-500' },
  PENDING: { badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400', dot: 'bg-amber-500' },
  DELETED: { badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300', dot: 'bg-slate-400' },
};

const EVENT_ICON: Record<string, any> = {
  uploaded: FileText, consumed: FileText, scheduled_for_deletion: Clock,
  deleted: Trash2, delete_verified: CheckCircle, delete_failed: AlertTriangle,
  policy_changed: RefreshCw, manual_delete: Trash2,
};

const EVENT_STYLE: Record<string, string> = {
  uploaded: 'text-emerald-500', consumed: 'text-primary',
  scheduled_for_deletion: 'text-amber-500', deleted: 'text-rose-500',
  delete_verified: 'text-green-500', delete_failed: 'text-rose-500',
  policy_changed: 'text-muted-foreground', manual_delete: 'text-rose-500',
};

function PrivacyPage() {
  const [files, setFiles] = useState<PrivacyFile[]>([]);
  const [activity, setActivity] = useState<Activity[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [policy, setPolicy] = useState('');
  const [options, setOptions] = useState<PolicyOpt[]>([]);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoadError('');
    try {
      const res = await fetch('/api/privacy', { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setFiles(d.files || []);
      setActivity(d.activity || []);
      setStats(d.stats || null);
      setPolicy(d.policy || '');
      setOptions(d.options || []);
    } catch (e) {
      setLoadError('Backend unreachable — start the firewall backend on :8000');
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const t = setInterval(load, 5000); // live-ish refresh while request logs in
    return () => clearInterval(t);
  }, [load]);

  const act = async (action: string, extra?: Record<string, unknown>) => {
    setBusy(true);
    try {
      const res = await fetch('/api/privacy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...(extra || {}) }),
        cache: 'no-store',
      });
      await res.json();
      await load();
    } catch { /* ignore */ }
    finally { setBusy(false); }
  };

  const setRetention = (key: string) => act('policy', { policy: key });
  const deleteFile = (fid: string) => act('delete', { fid });

  return (
    <div className="min-h-screen bg-background gradient-mesh">
      <div className="max-w-6xl mx-auto p-4 sm:p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 sm:p-3 rounded-xl bg-primary/10 border border-primary/20">
              <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                AI Data Auto-Deletion
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
                Secure upload tracking · verified cleanup · retention policies
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-sm">
              <LayoutDashboard className="w-4 h-4" /> Dashboard
            </Link>
            <button onClick={load} className="p-2 hover:bg-muted rounded-lg transition-colors border border-border" title="Refresh">
              <RefreshCw className={cn('w-5 h-5', busy && 'animate-spin')} />
            </button>
          </div>
        </div>

        {loadError && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" /> {loadError}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <Stat label="Uploads" value={stats?.total_uploads ?? '—'} />
          <Stat label="Active" value={stats?.active ?? '—'} />
          <Stat label="Pending delete" value={stats?.pending ?? '—'} />
          <Stat label="Deleted" value={stats?.deleted ?? '—'} />
          <Stat label="Verified clean" value={stats?.deleted_verified ?? '—'} />
          <Stat label="Delete failed" value={stats?.delete_failed ?? '—'} />
        </div>

        {/* Retention policy */}
        <section className="rounded-xl border bg-card p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Retention policy</h2>
              <span className="text-xs text-muted-foreground">applies to new uploads · auto-deleted &amp; verified after</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {options.map(o => (
                <button key={o.key} onClick={() => setRetention(o.key)}
                  className={cn('px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors',
                    policy === o.key ? 'bg-primary text-primary-foreground border-primary' : 'border-border hover:bg-muted')}>
                  {o.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        <div className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
          {/* Tracked files */}
          <section className="rounded-xl border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h2 className="text-sm font-semibold flex items-center gap-2"><FileText className="w-4 h-4" /> Tracked uploads</h2>
              <span className="text-xs text-muted-foreground">{files.length} recorded</span>
            </div>
            {files.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground text-center">No uploads tracked yet. Attach a file on the /chat page to see it here.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b border-border/50">
                      <th className="px-4 py-2">File</th>
                      <th className="px-4 py-2">Class</th>
                      <th className="px-4 py-2">Risk</th>
                      <th className="px-4 py-2">Lifecycle</th>
                      <th className="px-4 py-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((f) => {
                      const st = STATE_STYLE[f.state];
                      const notRetained = f.deleted_by === 'nothing_retained';
                      return (
                        <tr key={f.fid || f.filename + f.deleted_at} className="border-b border-border/40 table-row-hover">
                          <td className="px-4 py-2.5">
                            <div className="font-mono text-xs text-foreground truncate max-w-[180px]">{f.filename}</div>
                            <div className="text-[10px] text-muted-foreground">{formatBytes(f.size_bytes)} · {f.extension || 'bin'}</div>
                          </td>
                          <td className="px-4 py-2.5"><span className="text-xs text-muted-foreground">{f.classification}</span></td>
                          <td className="px-4 py-2.5"><RiskBadge level={f.risk_level} /></td>
                          <td className="px-4 py-2.5">
                            <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium', st.badge)}>
                              <span className={cn('w-1.5 h-1.5 rounded-full', st.dot)} />
                              {f.state}
                            </span>
                            {f.state === 'DELETED' && (
                              <div className="text-[10px] text-muted-foreground mt-0.5">
                                {notRetained ? 'never retained' : f.verified ? '✓ verified removed' : '✗ not verified'}
                                {f.deleted_at ? ` · ${f.deleted_at.split('T')[1]?.slice(0, 8) || ''}` : ''}
                              </div>
                            )}
                            {f.state !== 'DELETED' && <div className="text-[10px] text-muted-foreground mt-0.5">{f.consumed_at ? 'processed' : 'not yet used'}</div>}
                          </td>
                          <td className="px-4 py-2.5 text-right">
                            {f.state !== 'DELETED' ? (
                              <button onClick={() => deleteFile(f.fid)} disabled={busy || !f.fid}
                                className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border hover:bg-muted disabled:opacity-40">
                                <Trash2 className="w-3 h-3" /> Delete now
                              </button>
                            ) : <span className="text-[11px] text-muted-foreground">—</span>}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Activity log */}
          <section className="rounded-xl border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h2 className="text-sm font-semibold flex items-center gap-2"><RefreshCw className="w-4 h-4" /> Activity log</h2>
              <button onClick={() => act('sweep')} disabled={busy}
                className="text-[11px] px-2 py-1 rounded border border-border hover:bg-muted disabled:opacity-40">Sweep now</button>
            </div>
            {activity.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground text-center">No activity yet.</p>
            ) : (
              <div className="max-h-[440px] overflow-y-auto divide-y divide-border/40">
                {activity.map((a, i) => {
                  const Icon = EVENT_ICON[a.event] || FileText;
                  return (
                    <div key={i} className="px-4 py-2.5 text-xs">
                      <div className="flex items-center gap-2">
                        <Icon className={cn('w-3.5 h-3.5 shrink-0', EVENT_STYLE[a.event] || 'text-muted-foreground')} />
                        <span className="font-medium capitalize">{a.event.replace(/_/g, ' ')}</span>
                        {a.filename && <span className="text-muted-foreground truncate">{a.filename}</span>}
                        <span className="ml-auto text-[10px] text-muted-foreground shrink-0">{fmtTime(a.ts)}</span>
                      </div>
                      {a.detail && <p className="mt-0.5 text-[11px] text-muted-foreground">{a.detail}</p>}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border bg-card p-3 sm:p-4">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-xl sm:text-2xl font-bold font-mono">{value}</div>
    </div>
  );
}

function RiskBadge({ level }: { level: string }) {
  return (
    <span className={cn('px-2 py-0.5 text-[11px] font-semibold rounded-full',
      level === 'CRITICAL' && 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
      level === 'HIGH' && 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      level === 'MEDIUM' && 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
      level === 'LOW' && 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400')}>
      {level}
    </span>
  );
}

function fmtTime(ts?: string) {
  if (!ts) return '';
  const d = new Date(ts.length > 10 ? ts : ts + 'Z');
  return isNaN(d.getTime()) ? ts : d.toLocaleTimeString();
}

function formatBytes(b: number) {
  if (b >= 1024 * 1024) return (b / 1024 / 1024).toFixed(1) + ' MB';
  if (b >= 1024) return (b / 1024).toFixed(1) + ' KB';
  return b + ' B';
}

export default PrivacyPage;