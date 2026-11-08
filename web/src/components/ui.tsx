import { useMemo, useState, type ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, ChevronDown, ChevronUp, ChevronsUpDown, CircleAlert, CircleCheck, Inbox, Minus, TriangleAlert } from 'lucide-react';
import type { Health } from '../lib/metrics';
import { signedPct } from '../lib/format';

export function PageHeader({ title, subtitle, actions, eyebrow }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
        <h1 className="truncate text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-2">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Section({ title, hint, actions, children, className = '' }: { title: ReactNode; hint?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card avoid-break ${className}`}>
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">{title}</h2>
          {hint && <p className="mt-0.5 text-xs text-ink-3">{hint}</p>}
        </div>
        {actions}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export type GoodWhen = 'up' | 'down' | 'none';
export function Delta({ value, good = 'none', label = 'vs last month' }: { value: number | null | undefined; good?: GoodWhen; label?: string }) {
  if (value == null) return <span className="text-xs text-ink-3">No prior month</span>;
  const flat = Math.abs(value) < 0.0005;
  const up = value > 0;
  const isGood = good === 'none' || flat ? null : up === (good === 'up');
  const tone = isGood == null ? 'text-ink-3' : isGood ? 'text-good' : 'text-crit';
  const Icon = flat ? Minus : up ? ArrowUpRight : ArrowDownRight;
  const verdict = isGood == null ? '' : isGood ? ', an improvement' : ', a decline';
  return (
    <span className={`num inline-flex items-center gap-0.5 text-xs font-medium ${tone}`}>
      <Icon size={13} aria-hidden strokeWidth={2.25} />
      {signedPct(value)}
      <span className="sr-only">{` ${label}${verdict}`}</span>
      <span className="ml-1 font-normal text-ink-3" aria-hidden>{label}</span>
    </span>
  );
}

export function KpiCard({ label, value, delta, good, sub }: { label: string; value: ReactNode; delta?: number | null; good?: GoodWhen; sub?: ReactNode }) {
  return (
    <div className="card avoid-break p-4">
      <div className="text-xs font-medium text-ink-3">{label}</div>
      <div className="num mt-1.5 text-2xl font-semibold tracking-tight">{value}</div>
      <div className="mt-1.5 min-h-[16px]">
        {delta !== undefined ? <Delta value={delta} good={good} /> : sub}
      </div>
    </div>
  );
}

const HEALTH = {
  critical: { label: 'Critical', cls: 'bg-crit/10 text-crit border-crit/25', Icon: CircleAlert },
  warn: { label: 'Warning', cls: 'bg-warn/10 text-warn border-warn/25', Icon: TriangleAlert },
  healthy: { label: 'Healthy', cls: 'bg-good/10 text-good border-good/25', Icon: CircleCheck },
} as const;
export function HealthBadge({ health, count }: { health: Health; count?: number }) {
  const h = HEALTH[health];
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${h.cls}`}>
      <h.Icon size={12} aria-hidden />
      {h.label}
      {count ? <span className="num opacity-80">{`· ${count}`}</span> : null}
    </span>
  );
}
export function SeverityBadge({ severity }: { severity: string }) {
  return <HealthBadge health={severity === 'critical' ? 'critical' : 'warn'} />;
}
export function HealthDot({ health }: { health: Health }) {
  const c = { critical: 'bg-crit', warn: 'bg-warn', healthy: 'bg-good' }[health];
  return <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${c}`} role="img" aria-label={HEALTH[health].label} title={HEALTH[health].label} />;
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}
export function PageSkeleton() {
  return (
    <div role="status" aria-label="Loading">
      <Skeleton className="mb-6 h-7 w-64" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}</div>
      <Skeleton className="mt-4 h-72" />
    </div>
  );
}
export function EmptyState({ title, body, icon }: { title: string; body?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      <div className="mb-3 grid h-10 w-10 place-items-center rounded-full bg-subtle text-ink-3">{icon ?? <Inbox size={18} aria-hidden />}</div>
      <p className="text-sm font-medium">{title}</p>
      {body && <p className="mt-1 max-w-sm text-sm text-ink-2">{body}</p>}
    </div>
  );
}
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="card p-6" role="alert">
      <p className="text-sm font-semibold text-crit">Something went wrong</p>
      <p className="mt-1 text-sm text-ink-2">{message}</p>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, label }: { tabs: { id: T; label: string }[]; value: T; onChange: (t: T) => void; label: string }) {
  return (
    <div role="tablist" aria-label={label} className="no-print -mx-1 mb-5 flex gap-1 overflow-x-auto border-b border-line px-1">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} id={`tab-${t.id}`} aria-controls="tabpanel"
          onClick={() => onChange(t.id)}
          className={`relative -mb-px whitespace-nowrap px-3 py-2 text-sm font-medium transition-colors ${value === t.id ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}>
          {t.label}
          {value === t.id && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />}
        </button>
      ))}
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange, label }: { options: { id: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-line bg-subtle p-0.5">
      {options.map((o) => (
        <button key={o.id} role="radio" aria-checked={value === o.id} onClick={() => onChange(o.id)}
          className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${value === o.id ? 'bg-surface text-ink shadow-[0_0_0_1px_rgb(var(--line))]' : 'text-ink-3 hover:text-ink-2'}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export interface Column<T> {
  key: string; label: string; align?: 'right'; render: (r: T) => ReactNode;
  sort?: (r: T) => number | string | null; className?: string;
}
export function DataTable<T>({ rows, columns, rowKey, defaultSort, defaultDir = 'desc', caption, footer, empty }: {
  rows: T[]; columns: Column<T>[]; rowKey: (r: T) => string; defaultSort?: string; defaultDir?: 'asc' | 'desc'; caption: string; footer?: ReactNode; empty?: ReactNode;
}) {
  const [sort, setSort] = useState(defaultSort);
  const [dir, setDir] = useState(defaultDir);
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort);
    if (!col?.sort) return rows;
    const f = col.sort;
    const m = dir === 'asc' ? 1 : -1;
    return [...rows].sort((a, b) => {
      const x = f(a), y = f(b);
      if (x == null) return 1;
      if (y == null) return -1;
      return (typeof x === 'string' ? x.localeCompare(y as string) : x - (y as number)) * m;
    });
  }, [rows, columns, sort, dir]);
  if (!rows.length) return <>{empty ?? <EmptyState title="No data for this period" />}</>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line">
            {columns.map((c) => {
              const active = sort === c.key;
              const Icon = !active ? ChevronsUpDown : dir === 'asc' ? ChevronUp : ChevronDown;
              return (
                <th key={c.key} scope="col" className={`th ${c.align === 'right' ? 'text-right' : ''}`}
                  aria-sort={active ? (dir === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  {c.sort ? (
                    <button className={`inline-flex items-center gap-1 hover:text-ink ${c.align === 'right' ? 'flex-row-reverse' : ''} ${active ? 'text-ink' : ''}`}
                      onClick={() => { if (active) setDir(dir === 'asc' ? 'desc' : 'asc'); else { setSort(c.key); setDir(c.align === 'right' ? 'desc' : 'asc'); } }}>
                      {c.label}<Icon size={12} aria-hidden className={active ? '' : 'opacity-50'} />
                    </button>
                  ) : c.label}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={rowKey(r)} className="border-b border-line last:border-0 hover:bg-subtle/60">
              {columns.map((c) => <td key={c.key} className={`td ${c.align === 'right' ? 'num text-right' : ''} ${c.className ?? ''}`}>{c.render(r)}</td>)}
            </tr>
          ))}
        </tbody>
        {footer && <tfoot>{footer}</tfoot>}
      </table>
    </div>
  );
}
