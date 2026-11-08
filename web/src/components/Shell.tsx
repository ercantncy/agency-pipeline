import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Bell, LayoutDashboard, Menu, Moon, Search, Sun, X } from 'lucide-react';
import { useApp, useLink, useMonth, useTheme } from '../lib/app';
import { monthLabel } from '../lib/format';
import { healthOf } from '../lib/metrics';
import { HealthDot } from './ui';

function useCounts() {
  const m = useApp();
  const [month] = useMonth();
  return useMemo(() => m.clients.map((c) => {
    const k = c.alert_counts_by_month[month] ?? { critical: 0, warn: 0 };
    const health = healthOf([...Array(k.critical).fill({ severity: 'critical' }), ...Array(k.warn).fill({ severity: 'warn' })]);
    return { ...c, k, health };
  }), [m, month]);
}

function Logo() {
  const { agency } = useApp();
  return (
    <div className="flex items-center gap-2.5 px-2">
      <span className="grid h-7 w-7 place-items-center rounded-md bg-accent text-accent-fg"><BarChart3 size={16} aria-hidden /></span>
      <div className="min-w-0 leading-tight">
        <div className="truncate text-sm font-semibold">{agency.logo_text}</div>
        <div className="truncate text-2xs text-ink-3">Client reporting</div>
      </div>
    </div>
  );
}

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  const link = useLink();
  const counts = useCounts();
  const crit = counts.reduce((a, c) => a + c.k.critical, 0);
  const item = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors ${isActive ? 'bg-subtle font-medium text-ink' : 'text-ink-2 hover:bg-subtle hover:text-ink'}`;
  return (
    <nav aria-label="Primary" className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 pt-4">
      <NavLink to={link('/')} end className={item} onClick={onNavigate}><LayoutDashboard size={16} aria-hidden />Portfolio</NavLink>
      <NavLink to={link('/alerts')} className={item} onClick={onNavigate}>
        <Bell size={16} aria-hidden />Alerts
        {crit > 0 && <span className="num ml-auto rounded-full bg-crit/10 px-1.5 text-xs font-medium text-crit" aria-label={`${crit} critical alerts`}>{crit}</span>}
      </NavLink>
      <div className="eyebrow mt-5 px-2 pb-1">Clients</div>
      {counts.map((c) => (
        <NavLink key={c.client_id} to={link(`/clients/${c.client_id}`)} className={item} onClick={onNavigate}>
          <HealthDot health={c.health} /><span className="truncate">{c.client_name}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const counts = useCounts();
  const link = useLink();
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const items = useMemo(() => [
    { id: 'home', label: 'Portfolio overview', to: link('/') },
    { id: 'alerts', label: 'Alerts center', to: link('/alerts') },
    ...counts.map((c) => ({ id: c.client_id, label: c.client_name, to: link(`/clients/${c.client_id}`), health: c.health })),
  ].filter((i) => i.label.toLowerCase().includes(q.toLowerCase())), [counts, link, q]);
  useEffect(() => { if (open) { setQ(''); setSel(0); setTimeout(() => input.current?.focus(), 0); } }, [open]);
  useEffect(() => setSel(0), [q]);
  if (!open) return null;
  const go = (to: string) => { nav(to); onClose(); };
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[15vh]" onMouseDown={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Quick switcher" className="card w-full max-w-md overflow-hidden shadow-2xl" onMouseDown={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === 'Escape') onClose();
          if (e.key === 'ArrowDown') { e.preventDefault(); setSel((s) => Math.min(s + 1, items.length - 1)); }
          if (e.key === 'ArrowUp') { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
          if (e.key === 'Enter' && items[sel]) go(items[sel].to);
        }}>
        <div className="flex items-center gap-2 border-b border-line px-3">
          <Search size={15} className="text-ink-3" aria-hidden />
          <input ref={input} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Jump to a client or page…" aria-label="Search clients and pages"
            className="h-11 flex-1 bg-transparent text-sm outline-none placeholder:text-ink-3" />
        </div>
        <ul className="max-h-72 overflow-y-auto p-1.5">
          {items.map((i, idx) => (
            <li key={i.id}>
              <button onClick={() => go(i.to)} onMouseEnter={() => setSel(idx)}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm ${idx === sel ? 'bg-subtle' : ''}`}>
                {'health' in i && i.health ? <HealthDot health={i.health} /> : <span className="w-2" />}{i.label}
              </button>
            </li>
          ))}
          {!items.length && <li className="px-3 py-6 text-center text-sm text-ink-3">No matches</li>}
        </ul>
      </div>
    </div>
  );
}

export default function Shell() {
  const { months } = useApp();
  const [month, setMonth] = useMonth();
  const { theme, toggle } = useTheme();
  const [drawer, setDrawer] = useState(false);
  const [cmd, setCmd] = useState(false);
  const loc = useLocation();
  useEffect(() => { setDrawer(false); window.scrollTo(0, 0); }, [loc.pathname]);
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setCmd((o) => !o); } };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, []);
  return (
    <div className="min-h-screen lg:pl-60">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[60] focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Skip to content</a>
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-line bg-surface py-4 lg:flex" aria-label="Sidebar">
        <Logo /><Nav />
        <div className="px-4 pt-3 text-2xs text-ink-3">Synthetic demo data</div>
      </aside>
      {drawer && (
        <div className="fixed inset-0 z-40 lg:hidden" onClick={() => setDrawer(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col bg-surface py-4 shadow-xl" aria-label="Sidebar" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between pr-2"><Logo />
              <button className="icon-btn" aria-label="Close menu" onClick={() => setDrawer(false)}><X size={16} /></button></div>
            <Nav onNavigate={() => setDrawer(false)} />
          </aside>
        </div>
      )}
      <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-line bg-bg/85 px-4 backdrop-blur lg:px-8">
        <button className="icon-btn lg:hidden" aria-label="Open menu" onClick={() => setDrawer(true)}><Menu size={18} /></button>
        <Link to="/" className="mr-auto text-sm font-semibold lg:hidden">Reporting</Link>
        <button onClick={() => setCmd(true)} aria-label="Open quick switcher"
          className="mr-auto hidden h-8 w-72 items-center gap-2 rounded-md border border-line bg-surface px-2.5 text-sm text-ink-3 hover:border-line-strong lg:flex">
          <Search size={14} aria-hidden />Jump to client…<kbd className="ml-auto rounded border border-line px-1 text-2xs">⌘K</kbd>
        </button>
        <button className="icon-btn lg:hidden" aria-label="Open quick switcher" onClick={() => setCmd(true)}><Search size={16} /></button>
        <label className="sr-only" htmlFor="month">Reporting month</label>
        <select id="month" value={month} onChange={(e) => setMonth(e.target.value)}
          className="num h-8 rounded-md border border-line-strong bg-surface px-2 text-sm font-medium">
          {[...months].reverse().map((m) => <option key={m} value={m}>{monthLabel(m, true)}</option>)}
        </select>
        <button className="icon-btn" onClick={toggle} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </header>
      <main id="main" className="mx-auto max-w-[1200px] px-4 py-6 lg:px-8 lg:py-8"><Outlet /></main>
      <CommandPalette open={cmd} onClose={() => setCmd(false)} />
    </div>
  );
}
