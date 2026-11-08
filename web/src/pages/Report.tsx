import { useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Link2, Printer } from 'lucide-react';
import { useApp } from '../lib/app';
import { useClient } from '../lib/data';
import { CHANNEL_LABEL, GROUP_LABEL, dateRange, int, money, monthLabel, num1, pct, prevMonth, ratio } from '../lib/format';
import { alertRanges, alertsFor, inMonth, paidSeries, rowFor, sum } from '../lib/metrics';
import { C, Legend, TimeChart } from '../components/charts';
import { Delta, ErrorState, PageSkeleton, type GoodWhen } from '../components/ui';

function Block({ title, children, brk }: { title: string; children: ReactNode; brk?: boolean }) {
  return (
    <section className={`avoid-break mt-8 ${brk ? 'page-break' : ''}`}>
      <h2 className="mb-3 border-b border-line pb-2 text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}
function Stat({ label, value, delta, good }: { label: string; value: string; delta?: number | null; good?: GoodWhen }) {
  return (
    <div className="avoid-break rounded-lg border border-line p-3.5">
      <div className="text-xs text-ink-3">{label}</div>
      <div className="num mt-1 text-xl font-semibold">{value}</div>
      {delta !== undefined && <div className="mt-1"><Delta value={delta} good={good} /></div>}
    </div>
  );
}
function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <table className="w-full border-collapse text-sm">
      <thead><tr className="border-b border-line">{head.map((h, i) => <th key={h} className={`th ${i ? 'text-right' : ''}`}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => <tr key={i} className="avoid-break border-b border-line last:border-0">{r.map((v, j) => <td key={j} className={`td ${j ? 'num text-right' : 'font-medium'}`}>{v}</td>)}</tr>)}</tbody>
    </table>
  );
}

export default function Report() {
  const { clientId, month = '' } = useParams();
  const mf = useApp();
  const { data: c, error, loading } = useClient(clientId);
  const [copied, setCopied] = useState(false);
  if (loading) return <div className="mx-auto max-w-3xl p-8"><PageSkeleton /></div>;
  if (error || !c || !mf.months.includes(month)) return <div className="mx-auto max-w-xl p-8"><ErrorState message="This report could not be found." /></div>;
  const cur = c.client.currency;
  const brand = c.client.agency_primary_color;
  const t = rowFor(c, month);
  const pm = prevMonth(month);
  const alerts = alertsFor(c, month);
  const drops = alerts.filter((a) => a.check === 'volume_drop');
  const ranges = alertRanges(drops);
  const com = c.months[month]?.commentary;
  const chRows = (['google_ads', 'meta_ads'] as const).map((ch) => rowFor(c, month, ch)).filter((r) => !!r);
  const web = inMonth(c.web_daily, month), webPrev = c.web_daily.filter((r) => r.date.slice(0, 7) === pm);
  const ws = sum(web, (r) => r.sessions), wsp = sum(webPrev, (r) => r.sessions);
  const wk = sum(web, (r) => r.key_events), wr = sum(web, (r) => r.revenue);
  const groups = [...new Set(web.map((r) => r.channel_group))].map((g) => ({ g, s: sum(web.filter((r) => r.channel_group === g), (r) => r.sessions) })).sort((a, b) => b.s - a.s);
  const seo = inMonth(c.seo_daily, month);
  const sc = sum(seo, (r) => r.clicks), si = sum(seo, (r) => r.impressions);
  const scp = sum(inMonth(c.seo_daily, pm), (r) => r.clicks);
  const queries = c.seo_queries_monthly.filter((q) => q.month === month).sort((a, b) => b.clicks - a.clicks).slice(0, 8);
  const camps = c.campaigns_monthly.filter((r) => r.month === month).sort((a, b) => b.spend - a.spend);
  const dropWindows = ranges.map((r) => dateRange(r.start, r.end));
  const recAlerts = alerts.filter((a) => a.check !== 'volume_drop');
  const webSeries = groups.map((g, i) => ({ key: g.g, label: GROUP_LABEL(g.g), color: [C.s1, C.s2, C.s3, C.s4, C.s5, C.s6][i % 6] }));
  const byDate = new Map<string, Record<string, number | string>>();
  for (const r of web) { const e = byDate.get(r.date) ?? { date: r.date }; e[r.channel_group] = ((e[r.channel_group] as number) ?? 0) + r.sessions; byDate.set(r.date, e); }
  const webData = [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date))) as { date: string }[];

  return (
    <div data-theme="light" className="report-page min-h-screen bg-bg pb-16 text-ink">
      <div className="no-print sticky top-0 z-10 border-b border-line bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-[820px] items-center gap-2 px-4 py-2.5">
          <Link to={`/clients/${c.client.client_id}?month=${month}`} className="btn"><ArrowLeft size={14} aria-hidden />Back to app</Link>
          <span className="mr-auto hidden text-xs text-ink-3 sm:inline">Client-facing preview</span>
          <button className="btn" onClick={() => { navigator.clipboard?.writeText(window.location.href).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }, () => undefined); }}>
            {copied ? <Check size={14} aria-hidden /> : <Link2 size={14} aria-hidden />}{copied ? 'Copied' : 'Copy link'}</button>
          <button className="btn btn-primary" onClick={() => window.print()}><Printer size={14} aria-hidden />Print / Save PDF</button>
        </div>
      </div>

      <article className="mx-auto mt-6 max-w-[820px] rounded-xl border border-line bg-surface px-6 py-8 sm:px-12 sm:py-12 print:mt-0 print:max-w-none print:rounded-none print:border-0 print:p-0" aria-label={`${monthLabel(month, true)} report for ${c.client.client_name}`}>
        <header className="flex items-start justify-between gap-4 border-b-2 pb-6" style={{ borderColor: brand }}>
          <div>
            <div className="text-sm font-semibold tracking-tight" style={{ color: brand }}>{c.client.agency_logo_text}</div>
            <h1 className="mt-5 text-3xl font-semibold tracking-tight">{monthLabel(month, true)} performance report</h1>
            <p className="mt-1 text-base text-ink-2">Prepared for {c.client.client_name}</p>
          </div>
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-sm font-bold text-white" style={{ background: brand }} aria-hidden>{c.client.agency_logo_text.slice(0, 1)}</div>
        </header>

        <Block title="Executive summary">
          <p className="text-sm leading-relaxed text-ink-2">{com?.text ?? 'No commentary available for this month.'}</p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Paid spend" value={money(t?.spend, cur)} delta={t?.spend_mom_pct} good="none" />
            <Stat label="Conversions" value={int(t?.conversions)} delta={t?.conversions_mom_pct} good="up" />
            <Stat label="Cost per acquisition" value={money(t?.cpa, cur, { decimals: 2 })} delta={t?.cpa_mom_pct} good="down" />
            <Stat label="Return on ad spend" value={ratio(t?.roas)} delta={t?.roas_mom_pct} good="up" />
          </div>
        </Block>

        <Block title="Paid media" brk>
          <Legend items={[{ label: 'Google Ads', color: C.s1 }, { label: 'Meta Ads', color: C.s2 }]} />
          <TimeChart ariaLabel="Daily paid spend by channel" data={paidSeries(c, month, 'spend')} fmt={(v) => money(v, cur)} axisFmt={(v) => money(v, cur, { compact: true })} height={200}
            series={[{ key: 'google_ads', label: 'Google Ads', color: C.s1 }, { key: 'meta_ads', label: 'Meta Ads', color: C.s2 }]} />
          <div className="mt-4"><Table head={['Channel', 'Spend', 'Clicks', 'Conv.', 'CPA', 'ROAS']}
            rows={chRows.map((r) => [CHANNEL_LABEL[r!.channel], money(r!.spend, cur), int(r!.clicks), int(r!.conversions), money(r!.cpa, cur, { decimals: 2 }), ratio(r!.roas)])} /></div>
        </Block>

        <Block title="Campaign results">
          <Table head={['Campaign', 'Channel', 'Spend', 'Conv.', 'CPA']}
            rows={camps.map((r) => [r.campaign_name, CHANNEL_LABEL[r.channel], money(r.spend, cur), int(r.conversions), money(r.conversions ? r.spend / r.conversions : null, cur, { decimals: 2 })])} />
        </Block>

        <Block title="Website traffic" brk>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Sessions" value={int(ws)} delta={wsp && webPrev.length ? ws / wsp - 1 : null} good="up" />
            <Stat label="Key events" value={int(Math.round(wk))} />
            {wr > 0 && <Stat label="Revenue" value={money(wr, cur)} />}
          </div>
          <div className="mt-4"><Legend items={[...webSeries.map((s) => ({ label: s.label, color: s.color })), ...(ranges.length ? [{ label: 'Tracking gap', color: C.crit, shade: true }] : [])]} /></div>
          <TimeChart ariaLabel="Daily sessions by channel group" data={webData} series={webSeries} fmt={int} stack height={220} ranges={ranges.map((r) => ({ ...r, label: 'Tracking gap' }))} />
        </Block>

        <Block title="Organic search">
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Clicks" value={int(sc)} delta={scp ? sc / scp - 1 : null} good="up" />
            <Stat label="Impressions" value={int(si)} />
            <Stat label="Click-through rate" value={pct(si ? sc / si : null, 2)} />
          </div>
          <div className="mt-4"><Table head={['Top query', 'Clicks', 'Impressions', 'Avg. position']}
            rows={queries.map((q) => [q.query, int(q.clicks), int(q.impressions), num1(q.avg_position)])} /></div>
        </Block>

        {alerts.length > 0 && (
          <Block title="Data notes">
            <div className="rounded-lg border border-line bg-subtle p-4 text-sm leading-relaxed text-ink-2">
              {dropWindows.length > 0 && <>Website analytics data was incomplete during {dropWindows.join(' and ')}. Website sessions and key events for that period may be understated. </>}
              {recAlerts.length > 0 && <>{dropWindows.length > 0 ? '' : 'Some website visits from paid search could not be matched to ad clicks in analytics this month. '}Ad-platform figures (spend, clicks, conversions) are unaffected. </>}
              We are investigating and will confirm once resolved.
            </div>
          </Block>
        )}
        <footer className="mt-10 border-t border-line pt-4 text-xs text-ink-3">
          {c.client.agency_name} · Confidential, prepared for {c.client.client_name}. Figures in {cur}. Month-over-month changes compare with {monthLabel(pm, true)}.
        </footer>
      </article>
    </div>
  );
}
