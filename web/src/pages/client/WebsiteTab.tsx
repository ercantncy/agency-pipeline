import { TriangleAlert } from 'lucide-react';
import { useLink } from '../../lib/app';
import { Link } from 'react-router-dom';
import { GROUP_LABEL, dateRange, int, money, pct, prevMonth } from '../../lib/format';
import { alertRanges, alertsFor, inMonth, sum } from '../../lib/metrics';
import type { WebDaily } from '../../lib/types';
import { C, Legend, TimeChart, type Series } from '../../components/charts';
import { DataTable, EmptyState, KpiCard, Section, type Column } from '../../components/ui';
import type { TabProps } from './shared';

const ORDER = ['paid_search', 'paid_social', 'organic_search', 'direct', 'email', 'referral'];
const COLORS = [C.s1, C.s2, C.s3, C.s4, C.s5, C.s6];

export default function WebsiteTab({ c, month }: TabProps) {
  const link = useLink();
  const cur = c.client.currency;
  const rows = inMonth(c.web_daily, month);
  const prev = c.web_daily.filter((r) => r.date.slice(0, 7) === prevMonth(month));
  if (!rows.length) return <div className="card"><EmptyState title="No website data for this month" body="GA4 returned no sessions for the selected period." /></div>;
  const tot = (rs: WebDaily[]) => ({ s: sum(rs, (r) => r.sessions), u: sum(rs, (r) => r.users), e: sum(rs, (r) => r.engaged_sessions), k: sum(rs, (r) => r.key_events), rev: sum(rs, (r) => r.revenue) });
  const a = tot(rows), b = tot(prev);
  const d = (x: number, y: number) => (prev.length && y ? x / y - 1 : null);
  const groups = [...new Set(c.web_daily.map((r) => r.channel_group))].sort((x, y) => (ORDER.indexOf(x) + 99) % 99 - (ORDER.indexOf(y) + 99) % 99);
  const series: Series[] = groups.map((g, i) => ({ key: g, label: GROUP_LABEL(g), color: COLORS[i % COLORS.length] }));
  const byDate = new Map<string, Record<string, number | string>>();
  for (const r of rows) { const e = byDate.get(r.date) ?? { date: r.date }; e[r.channel_group] = ((e[r.channel_group] as number) ?? 0) + r.sessions; byDate.set(r.date, e); }
  const data = [...byDate.values()].sort((x, y) => String(x.date).localeCompare(String(y.date))) as { date: string }[];
  const alerts = alertsFor(c, month);
  const drops = alerts.filter((x) => x.check === 'volume_drop');
  const ranges = alertRanges(drops.length ? drops : alerts).map((r) => ({ ...r, label: 'Tracking outage' }));
  const gRows = groups.map((g) => { const rs = rows.filter((r) => r.channel_group === g); return { g, ...tot(rs) }; }).filter((x) => x.s > 0);
  type G = (typeof gRows)[number];
  const cols: Column<G>[] = [
    { key: 'g', label: 'Channel group', sort: (r) => r.g, render: (r) => <span className="inline-flex items-center gap-2 font-medium"><span className="h-2 w-2 rounded-full" style={{ background: series.find((s) => s.key === r.g)?.color }} />{GROUP_LABEL(r.g)}</span> },
    { key: 's', label: 'Sessions', align: 'right', sort: (r) => r.s, render: (r) => int(r.s) },
    { key: 'sh', label: 'Share', align: 'right', sort: (r) => r.s, render: (r) => pct(r.s / a.s, 0) },
    { key: 'er', label: 'Engagement', align: 'right', sort: (r) => r.e / r.s, render: (r) => pct(r.e / r.s, 0) },
    { key: 'k', label: 'Key events', align: 'right', sort: (r) => r.k, render: (r) => int(Math.round(r.k)) },
    { key: 'rev', label: 'Revenue', align: 'right', sort: (r) => r.rev, render: (r) => money(r.rev, cur) },
  ];
  return (
    <>
      {drops.length > 0 && (
        <div role="status" className="flex items-start gap-2 rounded-lg border border-crit/30 bg-crit/5 px-4 py-3 text-sm">
          <TriangleAlert size={16} className="mt-0.5 shrink-0 text-crit" aria-hidden />
          <div><span className="font-medium">Tracking outage detected, {dateRange(drops[0].start_date, drops[0].end_date)}.</span>{' '}
            <span className="text-ink-2">Sessions collapsed while ads kept running, so figures for those days are understated. </span>
            <Link to={link(`/clients/${c.client.client_id}`, { tab: 'data-quality' })} className="font-medium text-accent hover:underline">See reconciliation</Link></div>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <KpiCard label="Sessions" value={int(a.s)} delta={d(a.s, b.s)} good="up" />
        <KpiCard label="Users" value={int(a.u)} delta={d(a.u, b.u)} good="up" />
        <KpiCard label="Engagement rate" value={pct(a.s ? a.e / a.s : null, 0)} delta={d(a.s ? a.e / a.s : 0, b.s ? b.e / b.s : 0)} good="up" />
        <KpiCard label="Key events" value={int(Math.round(a.k))} delta={d(a.k, b.k)} good="up" />
        <KpiCard label="Revenue" value={money(a.rev, cur)} delta={d(a.rev, b.rev)} good="up" />
      </div>
      <Section title="Sessions by channel group" hint="GA4, stacked">
        <Legend items={[...series.map((s) => ({ label: s.label, color: s.color })), ...(ranges.length ? [{ label: 'Alert window', color: C.crit, shade: true }] : [])]} />
        <TimeChart ariaLabel="Daily website sessions by channel group" data={data} series={series} fmt={int} stack ranges={ranges} height={280} />
      </Section>
      <Section title="Channel groups"><div className="-mx-4 -my-4"><DataTable rows={gRows} columns={cols} rowKey={(r) => r.g} defaultSort="s" caption="Sessions by channel group" /></div></Section>
    </>
  );
}
