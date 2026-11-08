import { int, num1, pct, prevMonth } from '../../lib/format';
import { inMonth, sum } from '../../lib/metrics';
import type { SeoDaily, SeoQuery } from '../../lib/types';
import { C, TimeChart } from '../../components/charts';
import { DataTable, EmptyState, KpiCard, Section, type Column } from '../../components/ui';
import type { TabProps } from './shared';

export default function SeoTab({ c, month }: TabProps) {
  const rows = inMonth(c.seo_daily, month);
  if (!rows.length) return <div className="card"><EmptyState title="No Search Console data for this month" /></div>;
  const prev = inMonth(c.seo_daily, prevMonth(month));
  const t = (rs: SeoDaily[]) => { const cl = sum(rs, (r) => r.clicks), im = sum(rs, (r) => r.impressions);
    return { cl, im, ctr: im ? cl / im : 0, pos: im ? sum(rs, (r) => r.avg_position * r.impressions) / im : 0 }; };
  const a = t(rows), b = t(prev);
  const d = (x: number, y: number) => (prev.length && y ? x / y - 1 : null);
  const queries = c.seo_queries_monthly.filter((q) => q.month === month);
  const cols: Column<SeoQuery>[] = [
    { key: 'q', label: 'Query', sort: (r) => r.query, render: (r) => <span className="font-medium">{r.query}</span> },
    { key: 'c', label: 'Clicks', align: 'right', sort: (r) => r.clicks, render: (r) => int(r.clicks) },
    { key: 'i', label: 'Impressions', align: 'right', sort: (r) => r.impressions, render: (r) => int(r.impressions) },
    { key: 'ctr', label: 'CTR', align: 'right', sort: (r) => r.ctr, render: (r) => pct(r.ctr, 1) },
    { key: 'p', label: 'Avg. position', align: 'right', sort: (r) => r.avg_position, render: (r) => num1(r.avg_position) },
  ];
  return (
    <>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Organic clicks" value={int(a.cl)} delta={d(a.cl, b.cl)} good="up" />
        <KpiCard label="Impressions" value={int(a.im)} delta={d(a.im, b.im)} good="up" />
        <KpiCard label="CTR" value={pct(a.ctr, 2)} delta={d(a.ctr, b.ctr)} good="up" />
        <KpiCard label="Avg. position" value={num1(a.pos)} delta={d(a.pos, b.pos)} good="down" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Daily clicks" hint="Google Search Console">
          <TimeChart ariaLabel="Daily organic clicks" data={rows as unknown as { date: string }[]} series={[{ key: 'clicks', label: 'Clicks', color: C.s3 }]} fmt={int} height={220} />
        </Section>
        <Section title="Daily impressions">
          <TimeChart ariaLabel="Daily impressions" data={rows as unknown as { date: string }[]} series={[{ key: 'impressions', label: 'Impressions', color: C.s1 }]} fmt={int} axisFmt={(v) => new Intl.NumberFormat('en', { notation: 'compact' }).format(v)} height={220} />
        </Section>
      </div>
      <Section title="Top queries" hint={`${queries.length} queries · click a column to sort`}>
        <div className="-mx-4 -my-4"><DataTable rows={queries} columns={cols} rowKey={(r) => r.query} defaultSort="c" caption="Top search queries" /></div>
      </Section>
    </>
  );
}
