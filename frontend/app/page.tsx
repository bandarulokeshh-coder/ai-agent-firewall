'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Shield, AlertTriangle, CheckCircle, XCircle,
  Activity, Users, RefreshCw, Zap, Lock,
  TrendingUp, TrendingDown, Clock, Terminal,
  Moon, Sun, Download, Search, Filter, Menu, X,
  BarChart3, Settings, FileText, Bell, MessageSquare, ShieldCheck
} from 'lucide-react';
import Link from 'next/link';
import {
  AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell
} from 'recharts';
import { cn } from '@/lib/utils';

interface ToolCall {
  id: string;
  agent_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  decision: 'ALLOW' | 'APPROVE' | 'BLOCK' | 'PENDING';
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reason: string;
  timestamp: string;
  source?: 'agent' | 'chat';
}

interface SecurityEvent {
  id: string;
  agent_id: string;
  event_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  timestamp: string;
}

interface DashboardStats {
  total_agents: number;
  total_actions: number;
  blocked_count: number;
  pending_count: number;
  recent_events: ToolCall[];
}

interface PendingCall {
  id: string;
  agent_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  reason: string;
  timestamp: string;
}

const COLORS = {
  ALLOW: '#10b981',
  APPROVE: '#f59e0b',
  BLOCK: '#ef4444',
  PENDING: '#6b7280',
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
};

const DECISION_ICONS = {
  ALLOW: CheckCircle,
  APPROVE: AlertTriangle,
  BLOCK: XCircle,
  PENDING: Clock,
};

function ThemeToggle({ theme, setTheme }: { theme: string; setTheme: (t: string) => void }) {
  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg border border-border hover:bg-muted transition-colors"
      title="Toggle theme"
    >
      {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
    </button>
  );
}

function RiskBadge({ level }: { level: string }) {
  return (
    <span className={cn(
      'px-3 py-1 text-xs font-semibold rounded-full inline-flex items-center gap-1.5 transition-all',
      level === 'CRITICAL' && 'risk-critical text-rose-400',
      level === 'HIGH' && 'risk-high text-orange-400',
      level === 'MEDIUM' && 'risk-medium text-yellow-400',
      level === 'LOW' && 'risk-low text-emerald-400',
    )}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
      {level}
    </span>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  const Icon = DECISION_ICONS[decision as keyof typeof DECISION_ICONS] || Clock;
  return (
    <span className={cn(
      'flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full transition-all',
      decision === 'ALLOW' && 'decision-allow',
      decision === 'APPROVE' && 'decision-approve',
      decision === 'BLOCK' && 'decision-block',
      decision === 'PENDING' && 'decision-pending',
    )}>
      <Icon className="w-3.5 h-3.5" />
      {decision}
    </span>
  );
}

function StatsCard({ title, value, icon: Icon, trend, color, subtitle }: {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  trend?: 'up' | 'down';
  color?: string;
  subtitle?: string;
}) {
  return (
    <div className="stat-card glass border border-border rounded-xl p-6 hover:border-primary/50">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-muted-foreground font-medium">{title}</p>
          <p className="text-4xl font-bold mt-2 bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
            {value.toLocaleString()}
          </p>
          {subtitle && (
            <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
          )}
        </div>
        <div className={cn(
          'p-3 rounded-xl border',
          color || 'bg-primary/10 text-primary border-primary/20'
        )}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
      {trend && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          {trend === 'up' ? (
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          ) : (
            <TrendingDown className="w-4 h-4 text-rose-500" />
          )}
          <span className={trend === 'up' ? 'text-emerald-500' : 'text-rose-500'}>
            {trend === 'up' ? '+12%' : '-5%'}
          </span>
          <span className="text-muted-foreground">from last hour</span>
        </div>
      )}
    </div>
  );
}

function FilterBar({ filter, setFilter, search, setSearch }: {
  filter: string;
  setFilter: (f: string) => void;
  search: string;
  setSearch: (s: string) => void;
}) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search agents, tools..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
        />
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => setFilter('ALL')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            filter === 'ALL'
              ? 'bg-primary text-primary-foreground'
              : 'bg-card border border-border hover:bg-muted'
          )}
        >
          All
        </button>
        <button
          onClick={() => setFilter('BLOCK')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            filter === 'BLOCK'
              ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              : 'bg-card border border-border hover:bg-muted'
          )}
        >
          Blocked
        </button>
        <button
          onClick={() => setFilter('APPROVE')}
          className={cn(
            'px-4 py-2 rounded-lg text-sm font-medium transition-all',
            filter === 'APPROVE'
              ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
              : 'bg-card border border-border hover:bg-muted'
          )}
        >
          Pending
        </button>
      </div>
    </div>
  );
}

function LiveActivityFeed({ events, onSelect, filter, search }: {
  events: ToolCall[];
  onSelect?: (e: ToolCall) => void;
  filter: string;
  search: string;
}) {
  const filtered = events.filter(e => {
    const matchesFilter = filter === 'ALL' || e.decision === filter;
    const matchesSearch = !search ||
      e.agent_id.toLowerCase().includes(search.toLowerCase()) ||
      e.tool_name.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  return (
    <div className="glass border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-card to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
            <Terminal className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Live Agent Activity</h3>
            <p className="text-xs text-muted-foreground">Real-time tool call monitoring</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            LIVE
          </span>
          <button
            onClick={() => {
              const csv = [
                ['Timestamp', 'Agent', 'Tool', 'Decision', 'Risk Level', 'Risk Score', 'Reason'],
                ...filtered.map(e => [
                  e.timestamp,
                  e.agent_id,
                  e.tool_name,
                  e.decision,
                  e.risk_level,
                  e.risk_score.toString(),
                  e.reason
                ])
              ].map(row => row.join(',')).join('\n');

              const blob = new Blob([csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `activity-${new Date().toISOString()}.csv`;
              a.click();
            }}
            className="p-2 rounded-lg border border-border hover:bg-muted transition-colors"
            title="Export CSV"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Activity className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <p className="text-muted-foreground">
              {events.length === 0 ? 'Waiting for agent activity...' : 'No matching events'}
            </p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              {events.length === 0 ? 'Events will appear in real-time' : 'Try adjusting your filters'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Agent</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Tool</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Decision</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 20).map((event, idx) => (
                <tr
                  key={event.id}
                  onClick={() => onSelect?.(event)}
                  className="border-b border-border/50 table-row-hover cursor-pointer"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <td className="px-5 py-3 text-xs font-mono text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-xs font-medium text-foreground font-mono">
                      {event.agent_id.slice(0, 8)}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-1 rounded">
                        {event.tool_name}
                      </span>
                      {event.source === 'chat' && (
                        <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-foreground/10 text-muted-foreground">Chat</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3"><DecisionBadge decision={event.decision} /></td>
                  <td className="px-5 py-3"><RiskBadge level={event.risk_level} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function RiskDistributionChart({ events }: { events: ToolCall[] }) {
  const distribution = events.reduce((acc, e) => {
    acc[e.risk_level] = (acc[e.risk_level] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const data = [
    { name: 'LOW', value: distribution.LOW || 0, color: COLORS.LOW },
    { name: 'MEDIUM', value: distribution.MEDIUM || 0, color: COLORS.MEDIUM },
    { name: 'HIGH', value: distribution.HIGH || 0, color: COLORS.HIGH },
    { name: 'CRITICAL', value: distribution.CRITICAL || 0, color: COLORS.CRITICAL },
  ];

  return (
    <div className="glass border border-border rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-orange-500/10 border border-orange-500/20">
          <BarChart3 className="w-5 h-5 text-orange-500" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Risk Distribution</h3>
          <p className="text-xs text-muted-foreground">Threat level breakdown</p>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={110}
              paddingAngle={3}
              dataKey="value"
              nameKey="name"
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [value.toString(), 'actions']}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function DecisionTrendChart({ events }: { events: ToolCall[] }) {
  const last24h = events.filter(e =>
    new Date(e.timestamp) > new Date(Date.now() - 24 * 60 * 60 * 1000)
  );

  const hourly = last24h.reduce((acc, e) => {
    const hour = new Date(e.timestamp).getHours();
    const key = `${hour.toString().padStart(2, '0')}:00`;
    if (!acc[key]) acc[key] = { ALLOW: 0, APPROVE: 0, BLOCK: 0 };
    acc[key][e.decision as 'ALLOW' | 'APPROVE' | 'BLOCK']++;
    return acc;
  }, {} as Record<string, { ALLOW: number; APPROVE: number; BLOCK: number }>);

  const data = Array.from({ length: 24 }, (_, i) => {
    const key = `${i.toString().padStart(2, '0')}:00`;
    return {
      hour: key,
      ...(hourly[key] || { ALLOW: 0, APPROVE: 0, BLOCK: 0 })
    };
  });

  return (
    <div className="glass border border-border rounded-xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
          <TrendingUp className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Decisions (24h)</h3>
          <p className="text-xs text-muted-foreground">Hourly trend analysis</p>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorAllow" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.ALLOW} stopOpacity={0.4} />
                <stop offset="95%" stopColor={COLORS.ALLOW} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorApprove" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.APPROVE} stopOpacity={0.4} />
                <stop offset="95%" stopColor={COLORS.APPROVE} stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorBlock" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={COLORS.BLOCK} stopOpacity={0.4} />
                <stop offset="95%" stopColor={COLORS.BLOCK} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
            <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} />
            <Tooltip
              formatter={(value: number, name: string) => [value.toString(), name]}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
              }}
            />
            <Legend />
            <Area type="monotone" dataKey="ALLOW" stroke={COLORS.ALLOW} fillOpacity={1} fill="url(#colorAllow)" name="Allowed" strokeWidth={2} />
            <Area type="monotone" dataKey="APPROVE" stroke={COLORS.APPROVE} fillOpacity={1} fill="url(#colorApprove)" name="Approval Required" strokeWidth={2} />
            <Area type="monotone" dataKey="BLOCK" stroke={COLORS.BLOCK} fillOpacity={1} fill="url(#colorBlock)" name="Blocked" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PendingApprovals({ items, onResolve }: { items: PendingCall[]; onResolve: (id: string, action: 'approve' | 'reject') => void }) {
  return (
    <div className="glass border-2 border-yellow-500/30 rounded-xl overflow-hidden glow-warning">
      <div className="px-5 py-4 border-b border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-gradient-to-r from-yellow-500/5 to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Pending Human Approvals</h3>
            <p className="text-xs text-muted-foreground">Requires manual review</p>
          </div>
        </div>
        <span className="px-3 py-1.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 text-sm font-semibold">
          {items.length} pending
        </span>
      </div>
      <div className="max-h-96 overflow-y-auto overflow-x-auto">
        {items.length === 0 ? (
          <div className="p-12 text-center">
            <Lock className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <p className="text-muted-foreground">No actions waiting for review</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Medium-risk tool calls will appear here</p>
          </div>
        ) : (
          <table className="w-full min-w-[600px]">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Tool</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Risk</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Reason</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-5 py-3 text-xs font-mono text-muted-foreground whitespace-nowrap">
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-1 rounded whitespace-nowrap">
                      {item.tool_name}
                    </span>
                  </td>
                  <td className="px-5 py-3"><RiskBadge level={item.risk_level} /></td>
                  <td className="px-5 py-3 text-xs text-muted-foreground max-w-xs truncate" title={item.reason}>
                    {item.reason}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2 whitespace-nowrap">
                      <button
                        onClick={() => onResolve(item.id, 'approve')}
                        className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={() => onResolve(item.id, 'reject')}
                        className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-rose-500/20 text-rose-400 border border-rose-500/30 hover:bg-rose-500/30 transition-all"
                      >
                        ✕ Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function SecurityAlerts({ events }: { events: SecurityEvent[] }) {
  return (
    <div className="glass border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between bg-gradient-to-r from-card to-transparent">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
            <Shield className="w-5 h-5 text-rose-500" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">Security Events</h3>
            <p className="text-xs text-muted-foreground">HIGH/CRITICAL severity alerts</p>
          </div>
        </div>
      </div>
      <div className="max-h-96 overflow-y-auto">
        {events.length === 0 ? (
          <div className="p-12 text-center">
            <Shield className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <p className="text-muted-foreground">No security events</p>
            <p className="text-xs text-muted-foreground/60 mt-1">All clear! No threats detected</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Type</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Severity</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">Description</th>
              </tr>
            </thead>
            <tbody>
              {events.slice(0, 15).map((event) => (
                <tr key={event.id} className="border-b border-border/50 table-row-hover">
                  <td className="px-5 py-3 text-xs font-mono text-muted-foreground">
                    {new Date(event.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-5 py-3">
                    <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded">
                      {event.event_type}
                    </span>
                  </td>
                  <td className="px-5 py-3"><RiskBadge level={event.severity} /></td>
                  <td className="px-5 py-3 text-xs text-muted-foreground max-w-xs truncate">
                    {event.description}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ToolCallDetailModal({ event, onClose }: { event: ToolCall | null; onClose: () => void }) {
  if (!event) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in" onClick={onClose}>
      <div className="glass border border-border rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-slide-up shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-5 border-b border-border flex items-center justify-between bg-gradient-to-r from-card to-transparent">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
              <Terminal className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-lg font-semibold">Tool Call Details</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground block mb-2 font-medium">Decision</label>
              <DecisionBadge decision={event.decision} />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-2 font-medium">Risk Level</label>
              <RiskBadge level={event.risk_level} />
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-2 font-medium">Risk Score</label>
            <div className="space-y-2">
              <div className="h-3 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${event.risk_score}%`,
                    backgroundColor: COLORS[event.risk_level as keyof typeof COLORS]
                  }}
                />
              </div>
              <p className="text-sm font-mono text-muted-foreground">{event.risk_score}/100</p>
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-2 font-medium">Tool</label>
            <code className="text-sm bg-primary/10 text-primary px-3 py-1.5 rounded-lg font-mono">{event.tool_name}</code>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-2 font-medium">Reason</label>
            <p className="text-sm text-foreground bg-muted p-4 rounded-lg border border-border">{event.reason || 'No issues detected'}</p>
          </div>

          <div>
            <label className="text-xs text-muted-foreground block mb-2 font-medium">Arguments</label>
            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto max-h-48 border border-border font-mono">
              {JSON.stringify(event.arguments, null, 2)}
            </pre>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted-foreground block mb-2 font-medium">Call ID</label>
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono break-all">{event.id}</code>
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-2 font-medium">Timestamp</label>
              <p className="text-sm font-mono">{new Date(event.timestamp).toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    total_agents: 0,
    total_actions: 0,
    blocked_count: 0,
    pending_count: 0,
    recent_events: [],
  });
  const [pendingApprovals, setPendingApprovals] = useState<PendingCall[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<ToolCall | null>(null);
  const [connected, setConnected] = useState(false);
  const [theme, setTheme] = useState('dark');
  const [filter, setFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/dashboard');
        if (!res.ok) throw new Error(`dashboard: ${res.status}`);
        const data = await res.json();
        setStats(data);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      }
    };

    const fetchPending = async () => {
      try {
        const res = await fetch('/api/pending');
        if (!res.ok) throw new Error(`pending: ${res.status}`);
        const data = await res.json();
        setPendingApprovals(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to fetch pending approvals:', err);
      }
    };

    const fetchSecurityEvents = async () => {
      try {
        const res = await fetch('/api/security-events');
        if (!res.ok) return;
        const data = await res.json();
        if (Array.isArray(data)) setSecurityEvents(data);
        else if (Array.isArray(data.items)) setSecurityEvents(data.items);
      } catch (err) {
        console.error('Failed to fetch security events:', err);
      }
    };

    const refreshAll = async () => {
      await fetchStats();
      await fetchPending();
      await fetchSecurityEvents();
    };

    refreshAll();
    const interval = setInterval(refreshAll, 5000);
    return () => clearInterval(interval);
  }, []);

  const resolvePending = async (id: string, action: 'approve' | 'reject') => {
    try {
      const res = await fetch(`/api/tool-call/${id}/${action}`, { method: 'POST' });
      if (!res.ok) {
        console.error(`Failed to ${action} tool call: ${res.status}`);
        return;
      }
      setPendingApprovals(prev => prev.filter(p => p.id !== id));
      const dash = await fetch('/api/dashboard');
      if (dash.ok) setStats(await dash.json());
    } catch (err) {
      console.error(`Failed to ${action} tool call:`, err);
    }
  };

  useEffect(() => {
    let websocket: WebSocket | null = null;
    let closed = false;
    const connectWS = () => {
      if (closed) return;
      const envUrl = process.env.NEXT_PUBLIC_WS_URL;
      const wsUrl = envUrl || `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws`;
      websocket = new WebSocket(wsUrl);

      websocket.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
      };
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        websocket?.close();
      };
      websocket.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnected(false);
        if (!closed) reconnectTimeout.current = setTimeout(connectWS, 3000);
      };
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'tool_call') {
            const normalized = {
              id: data.id || data.call_id,
              agent_id: data.agent_id,
              tool_name: data.tool_name,
              arguments: data.arguments || {},
              decision: data.decision,
              risk_score: data.risk_score ?? 0,
              risk_level: data.risk_level || 'LOW',
              reason: data.reason || '',
              timestamp: data.timestamp || new Date().toISOString(),
              source: 'agent' as const,
            };
            setStats(prev => ({
              ...prev,
              total_actions: prev.total_actions + 1,
              blocked_count: data.decision === 'BLOCK' ? prev.blocked_count + 1 : prev.blocked_count,
              recent_events: [normalized, ...prev.recent_events].slice(0, 100),
            }));
          } else if (data.type === 'approval_request') {
            setPendingApprovals(prev => [{
              id: data.id || data.call_id,
              agent_id: data.agent_id,
              tool_name: data.tool_name,
              arguments: data.arguments || {},
              risk_score: data.risk_score ?? 0,
              risk_level: data.risk_level || 'MEDIUM',
              reason: data.reason || '',
              timestamp: data.timestamp || new Date().toISOString(),
            }, ...prev].slice(0, 100));
          } else if (data.type === 'security_event') {
            setSecurityEvents(prev => [{
              id: data.id || `${data.event_type}-${data.timestamp || Date.now()}`,
              agent_id: data.agent_id || '',
              event_type: data.event_type || 'SECURITY',
              severity: data.severity || 'HIGH',
              description: data.description || '',
              timestamp: data.timestamp || new Date().toISOString(),
            }, ...prev].slice(0, 100));
          } else if (data.type === 'ai_request') {
            // Chat requests from /chat: mirror them onto the dashboard live feed
            // so whatever is asked on the chat page is visible/accessible here.
            const normalized = {
              id: data.id || `ai-${data.timestamp || Date.now()}`,
              agent_id: data.agent_id || data.session_id || data.provider || 'ai-chat',
              tool_name: data.model || 'AI_CHAT',
              arguments: { prompt_length: data.prompt_length ?? 0, file_count: data.file_count ?? 0 },
              decision: data.decision || 'PENDING',
              risk_score: data.risk_score ?? 0,
              risk_level: data.risk_level || 'LOW',
              reason: `pii ${data.pii_count ?? 0} secrets ${data.secret_count ?? 0} injection ${data.injection_score ?? 0}`,
              timestamp: data.timestamp || new Date().toISOString(),
              source: 'chat' as const,
            };
            setStats(prev => ({
              ...prev,
              total_actions: prev.total_actions + 1,
              blocked_count: data.decision === 'BLOCK' ? prev.blocked_count + 1 : prev.blocked_count,
              recent_events: [normalized, ...prev.recent_events].slice(0, 100),
            }));
          }
        } catch (err) {
          console.error('WS parse error:', err);
        }
      };

    };

    connectWS();
    return () => {
      closed = true;
      websocket?.close();
      clearTimeout(reconnectTimeout.current);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background gradient-mesh">
      <div className="max-w-7xl mx-auto p-4 sm:p-6 md:p-8 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="p-2 sm:p-3 rounded-xl bg-primary/10 border border-primary/20">
              <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                AI Agent Firewall
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">Runtime security layer for AI agents</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={cn(
              'hidden sm:flex items-center gap-2 px-3 sm:px-4 py-2 rounded-full text-xs sm:text-sm font-medium border',
              connected
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            )}>
              <span className="relative flex h-2 w-2">
                <span className={cn(
                  'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
                  connected ? 'bg-emerald-400' : 'bg-rose-400'
                )}></span>
                <span className={cn(
                  'relative inline-flex rounded-full h-2 w-2',
                  connected ? 'bg-emerald-500' : 'bg-rose-500'
                )}></span>
              </span>
              <span className="hidden sm:inline">{connected ? 'Connected' : 'Disconnected'}</span>
            </div>
            <ThemeToggle theme={theme} setTheme={setTheme} />
            <Link
              href="/chat"
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-sm"
            >
              <MessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">Chat</span>
            </Link>
            <Link
              href="/privacy"
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border hover:bg-muted transition-colors text-sm"
            >
              <ShieldCheck className="w-4 h-4" />
              <span className="hidden sm:inline">Privacy</span>
            </Link>
            <button
              onClick={async () => {
                try {
                  const res = await fetch('/api/dashboard');
                  const data = await res.json();
                  setStats(data);
                  const pending = await fetch('/api/pending');
                  const pendingData = await pending.json();
                  setPendingApprovals(Array.isArray(pendingData) ? pendingData : []);
                } catch (err) {
                  console.error('Refresh failed:', err);
                }
              }}
              className="p-2 hover:bg-muted rounded-lg transition-colors border border-border"
              title="Refresh"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Active Agents"
            value={stats.total_agents}
            icon={Users}
            color="bg-primary/10 text-primary border-primary/20"
          />
          <StatsCard
            title="Total Actions"
            value={stats.total_actions}
            icon={Zap}
            color="bg-primary/10 text-primary border-primary/20"
          />
          <StatsCard
            title="Blocked"
            value={stats.blocked_count}
            icon={XCircle}
            color="bg-rose-500/10 text-rose-400 border-rose-500/20"
          />
          <StatsCard
            title="Block Rate"
            value={stats.total_actions > 0 ? Math.round((stats.blocked_count / stats.total_actions) * 100) : 0}
            icon={Shield}
            color="bg-purple-500/10 text-purple-400 border-purple-500/20"
            subtitle={stats.total_actions > 0 ? `${stats.total_actions} total` : 'No data'}
          />
        </div>

        {/* Filters */}
        <FilterBar filter={filter} setFilter={setFilter} search={search} setSearch={setSearch} />

        {/* Pending Approvals */}
        <PendingApprovals items={pendingApprovals} onResolve={resolvePending} />

        {/* Live Activity & Security Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LiveActivityFeed events={stats.recent_events} onSelect={setSelectedEvent} filter={filter} search={search} />
          <SecurityAlerts events={securityEvents} />
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RiskDistributionChart events={stats.recent_events} />
          <DecisionTrendChart events={stats.recent_events} />
        </div>
      </div>

      <ToolCallDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
}
