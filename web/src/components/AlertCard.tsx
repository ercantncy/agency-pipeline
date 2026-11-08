import { Link } from 'react-router-dom';
import { CalendarRange } from 'lucide-react';
import type { Alert } from '../lib/types';
import { CHECK_LABEL, dateRange, daysBetween } from '../lib/format';
import { SeverityBadge } from './ui';

export default function AlertCard({ alert, clientName, to }: { alert: Alert; clientName?: string; to?: string }) {
  const crit = alert.severity === 'critical';
  return (
    <article className={`avoid-break rounded-lg border border-line bg-surface p-3.5 border-l-[3px] ${crit ? 'border-l-crit' : 'border-l-warn'}`}>
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={alert.severity} />
        <span className="rounded-md bg-subtle px-1.5 py-0.5 text-xs font-medium text-ink-2">{CHECK_LABEL(alert.check)}</span>
        {clientName && (to ? <Link to={to} className="text-sm font-medium hover:underline">{clientName}</Link> : <span className="text-sm font-medium">{clientName}</span>)}
        <span className="num ml-auto inline-flex items-center gap-1 text-xs text-ink-3">
          <CalendarRange size={12} aria-hidden />{dateRange(alert.start_date, alert.end_date)} · {daysBetween(alert.start_date, alert.end_date)}d
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">{alert.message}</p>
    </article>
  );
}
