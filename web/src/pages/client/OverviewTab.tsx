import { Link } from 'react-router-dom';
import { Sparkles, TriangleAlert } from 'lucide-react';
import { useLink } from '../../lib/app';
import { CHANNEL_LABEL, int, money, ratio } from '../../lib/format';
import { alertsFor, paidSeries, rowFor } from '../../lib/metrics';
import { C, Legend, TimeChart } from '../../components/charts';
import { DataTable, KpiCard, Section, type Column } from '../../components/ui';
import type { MonthlyRow } from '../../lib/types';
import type { TabProps } from './shared';

export default function OverviewTab({ c, month }: TabProps) {
  const link = useLink();
  const cur = c.client.currency;
  const t = rowFor(c, month);
  const alerts = alertsFor(c, month);
  const com = c.months[month]?.commentary;
  const rows = (['google_ads', 'meta_ads'] as const).map((ch) => rowFor(c, month, ch)).filter((r): r is MonthlyRow => !!r);
  const cols: Column<MonthlyRow>[] = [
    { key: 'ch', label: 'Channel', render: (r) => <span className="inline-flex items-center gap-2 font-medium"><span className="h-2 w-2 rounded-full" style={{ background: r.channel === 'google_ads' ? C.s1 : C.s2 }} />{CHANNEL_LABEL[r.channel]}</span> },
    { key: 'sp', label: 'Spend', align: 'right', sort: (r) => r.spend, render: (r) => money(r.spend, cur) },
    { key: 'cv', label: 'Conv.', align: 'right', sort: (r) => r.conversions, render: (r) => int(r.conversions) },
    { key: 'cpa', label: 'CPA', align: 'right', sort: (r) => r.cpa, render: (r) => money(r.cpa, cur, { decimals: 2 }) },
    { key: 'roas', label: 'ROAS', align: 'right', sort: (r) => r.roas, render: (r) => ratio(r.roas) },
  ];
  return (
    <>
      {alerts.length > 0 && (
        <div role="status" className="flex flex-wrap items-center gap-2 rounded-lg border border-crit/30 bg-crit/5 px-4 py-3 text-sm">
          <TriangleAlert size={16} className="text-crit" aria-hidden />
          <span className="font-medium">{alerts.length} data-quality alert{alerts.length > 1 ? 's' : ''} this month.</span>
          <span className="text-ink-2">Web figures may be unreliable.</span>
          <Link to={link(`/clients/${c.client.client_id}`, { tab: 'data-quality' })} className="ml-auto font-medium text-accent hover:underline">Review</Link>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Paid spend" value={money(t?.spend, cur)} delta={t?.spend_mom_pct} good="none" />
        <KpiCard label="Conversions" value={int(t?.conversions)} delta={t?.conversions_mom_pct} good="up" />
        <KpiCard label="Cost per acquisition" value={money(t?.cpa, cur, { decimals: 2 })} delta={t?.cpa_mom_pct} good="down" />
        <KpiCard label="ROAS" value={ratio(t?.roas)} delta={t?.roas_mom_pct} good="up" />
      </div>
      {com && (
        <Section title="Summary" actions={<span className="inline-flex items-center gap-1 text-xs text-ink-3"><Sparkles size={12} aria-hidden />{com.source === 'template' ? 'Auto-generated' : 'AI-assisted'}</span>}>
          <p className="max-w-3xl text-sm leading-relaxed text-ink-2">{com.text}</p>
        </Section>
      )}
      <Section title="Daily paid spend" hint="By channel">
        <Legend items={[{ label: 'Google Ads', color: C.s1 }, { label: 'Meta Ads', color: C.s2 }]} />
        <TimeChart ariaLabel="Daily paid spend by channel" data={paidSeries(c, month, 'spend')} fmt={(v) => money(v, cur)} axisFmt={(v) => money(v, cur, { compact: true })}
          series={[{ key: 'google_ads', label: 'Google Ads', color: C.s1 }, { key: 'meta_ads', label: 'Meta Ads', color: C.s2 }]} />
      </Section>
      <Section title="Channel summary">
        <div className="-mx-4 -my-4"><DataTable rows={rows} columns={cols} rowKey={(r) => r.channel} caption="Channel summary" defaultSort="sp" /></div>
      </Section>
    </>
  );
}
