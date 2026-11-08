import { useState } from 'react';
import { CHANNEL_LABEL, int, money, monthLabel, pct, ratio } from '../../lib/format';
import { paidSeries, rowFor } from '../../lib/metrics';
import type { MonthlyChannel, MonthlyRow } from '../../lib/types';
import { C, Legend, TimeChart, type Series } from '../../components/charts';
import { DataTable, KpiCard, Section, Segmented, type Column } from '../../components/ui';
import type { TabProps } from './shared';

export default function PaidTab({ c, month }: TabProps) {
  const [ch, setCh] = useState<MonthlyChannel>('total_paid');
  const cur = c.client.currency;
  const r = rowFor(c, month, ch);
  const series: Series[] = ch === 'total_paid'
    ? [{ key: 'google_ads', label: 'Google Ads', color: C.s1 }, { key: 'meta_ads', label: 'Meta Ads', color: C.s2 }]
    : ch === 'google_ads' ? [{ key: 'google_ads', label: 'Google Ads', color: C.s1 }] : [{ key: 'meta_ads', label: 'Meta Ads', color: C.s2 }];
  const trend = c.monthly.filter((m) => m.channel === ch).sort((a, b) => b.month.localeCompare(a.month));
  const cols: Column<MonthlyRow>[] = [
    { key: 'm', label: 'Month', render: (x) => <span className={x.month === month ? 'font-medium' : ''}>{monthLabel(x.month)}</span> },
    { key: 'sp', label: 'Spend', align: 'right', render: (x) => money(x.spend, cur) },
    { key: 'cl', label: 'Clicks', align: 'right', render: (x) => int(x.clicks) },
    { key: 'ctr', label: 'CTR', align: 'right', render: (x) => pct(x.ctr, 2) },
    { key: 'cv', label: 'Conv.', align: 'right', render: (x) => int(x.conversions) },
    { key: 'cpa', label: 'CPA', align: 'right', render: (x) => money(x.cpa, cur, { decimals: 2 }) },
    { key: 'roas', label: 'ROAS', align: 'right', render: (x) => ratio(x.roas) },
  ];
  const chart = (metric: 'spend' | 'clicks' | 'conversions', title: string, fmt: (v: number) => string, axis?: (v: number) => string) => (
    <Section title={title}>
      <Legend items={series.map((s) => ({ label: s.label, color: s.color }))} />
      <TimeChart ariaLabel={`${title} by day`} data={paidSeries(c, month, metric)} series={series} fmt={fmt} axisFmt={axis} stack={ch === 'total_paid'} height={220} />
    </Section>
  );
  return (
    <>
      <div className="flex justify-end"><Segmented label="Channel" value={ch} onChange={setCh}
        options={(['total_paid', 'google_ads', 'meta_ads'] as const).map((id) => ({ id, label: id === 'total_paid' ? 'All paid' : CHANNEL_LABEL[id] }))} /></div>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Spend" value={money(r?.spend, cur)} delta={r?.spend_mom_pct} good="none" />
        <KpiCard label="Conversions" value={int(r?.conversions)} delta={r?.conversions_mom_pct} good="up" />
        <KpiCard label="CPA" value={money(r?.cpa, cur, { decimals: 2 })} delta={r?.cpa_mom_pct} good="down" />
        <KpiCard label="ROAS" value={ratio(r?.roas)} delta={r?.roas_mom_pct} good="up" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        {chart('spend', 'Daily spend', (v) => money(v, cur), (v) => money(v, cur, { compact: true }))}
        {chart('conversions', 'Daily conversions', (v) => int(Math.round(v)))}
      </div>
      {chart('clicks', 'Daily clicks', int)}
      <Section title="Monthly trend"><div className="-mx-4 -my-4"><DataTable rows={trend} columns={cols} rowKey={(x) => x.month} caption="Monthly trend" /></div></Section>
    </>
  );
}
