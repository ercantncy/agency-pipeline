import { CircleCheck, Info } from 'lucide-react';
import { CHANNEL_LABEL, int, pct } from '../../lib/format';
import { alertRanges, alertsFor, inMonth, sum } from '../../lib/metrics';
import type { Channel, ReconRow } from '../../lib/types';
import AlertCard from '../../components/AlertCard';
import { C, CHANNEL_COLOR, Legend, TimeChart } from '../../components/charts';
import { DataTable, EmptyState, HealthBadge, Section, type Column } from '../../components/ui';
import type { TabProps } from './shared';

const SESSION_NAME: Record<Channel, string> = { google_ads: 'paid-search', meta_ads: 'paid-social' };

export default function DataQualityTab({ c, month }: TabProps) {
  const alerts = alertsFor(c, month);
  const recon = inMonth(c.reconciliation_daily, month);
  const channels = (['google_ads', 'meta_ads'] as Channel[]).filter((ch) => recon.some((r) => r.channel === ch));
  const th = c.thresholds;

  const sumRows = channels.map((ch) => {
    const rs = recon.filter((r) => r.channel === ch);
    const cl = sum(rs, (r) => r.platform_clicks), se = sum(rs, (r) => r.ga4_sessions);
    const flagged = rs.filter((r) => r.status !== 'ok').length;
    const worst = rs.reduce<number | null>((m, r) => (r.session_click_ratio != null && (m == null || r.session_click_ratio < m) ? r.session_click_ratio : m), null);
    return { ch, cl, se, ratio: cl ? se / cl : null, flagged, days: rs.length, worst, conv: sum(rs, (r) => r.platform_conversions), ke: sum(rs, (r) => r.ga4_key_events) };
  });
  type S = (typeof sumRows)[number];
  const cols: Column<S>[] = [
    { key: 'ch', label: 'Channel', render: (r) => <span className="inline-flex items-center gap-2 font-medium"><span className="h-2 w-2 rounded-full" style={{ background: CHANNEL_COLOR[r.ch] }} />{CHANNEL_LABEL[r.ch]}</span> },
    { key: 'cl', label: 'Platform clicks', align: 'right', render: (r) => int(r.cl) },
    { key: 'se', label: 'GA4 sessions', align: 'right', render: (r) => int(r.se) },
    { key: 'r', label: 'Month ratio', align: 'right', render: (r) => <span className="font-medium">{pct(r.ratio, 0)}</span> },
    { key: 'w', label: 'Worst day', align: 'right', render: (r) => pct(r.worst, 0) },
    { key: 'f', label: 'Flagged days', align: 'right', render: (r) => (
      <span className={r.flagged ? 'inline-flex items-center gap-1 font-medium text-crit' : 'text-ink-2'}>{r.flagged ? '⚠ ' : ''}{r.flagged} of {r.days}</span>) },
  ];

  return (
    <>
      <Section title="How reconciliation works" className="bg-subtle/40">
        <div className="flex gap-3">
          <Info size={16} className="mt-0.5 shrink-0 text-accent" aria-hidden />
          <div className="max-w-3xl space-y-2 text-sm leading-relaxed text-ink-2">
            <p>Every ad click should land a visitor on the website, and Google Analytics (GA4) should record that visit as a session. The two numbers never match exactly, because some people leave before the page loads and others block tracking, but they should rise and fall together.</p>
            <p>Each day we divide <strong className="font-medium text-ink">GA4 sessions by ad-platform clicks</strong>. A ratio near 100% means tracking is healthy. When it drops below the dashed
              <span className="font-medium text-warn"> warning line</span> or the <span className="font-medium text-crit">critical line</span>, something upstream is probably broken, such as auto-tagging switched off, a redirect stripping parameters, or the GA4 tag not firing.</p>
            <p className="text-xs text-ink-3">Thresholds: Google Ads warn below {pct(th.google_ads.warn, 0)}, critical below {pct(th.google_ads.critical, 0)}. Meta Ads warn below {pct(th.meta_ads.warn, 0)}, critical below {pct(th.meta_ads.critical, 0)}. Meta is lower because social clicks include in-app browsers that often never reach GA4.</p>
          </div>
        </div>
      </Section>

      <section aria-label="Alerts" className="space-y-3">
        <div className="flex items-center gap-2"><h2 className="text-sm font-semibold">Alerts</h2><HealthBadge health={alerts.some((a) => a.severity === 'critical') ? 'critical' : alerts.length ? 'warn' : 'healthy'} count={alerts.length} /></div>
        {alerts.length ? alerts.map((a, i) => <AlertCard key={i} alert={a} />) : (
          <div className="card"><EmptyState icon={<CircleCheck size={18} aria-hidden />} title="All checks passed" body="Click-to-session ratios and traffic volumes stayed within normal ranges all month." /></div>
        )}
      </section>

      {channels.length === 0 ? <div className="card"><EmptyState title="No reconciliation data for this month" /></div> : (
        <div className="grid gap-6 lg:grid-cols-2">
          {channels.map((ch) => {
            const mine = alerts.filter((a) => a.check !== 'reconciliation' || a.message.includes(CHANNEL_LABEL[ch]));
            const ranges = alertRanges(mine).map((r) => ({ ...r, label: 'Alert window' }));
            const data = recon.filter((r: ReconRow) => r.channel === ch).sort((a, b) => a.date.localeCompare(b.date)).map((r) => ({ date: r.date, ratio: r.session_click_ratio }));
            return (
              <Section key={ch} title={`${CHANNEL_LABEL[ch]}: sessions per click`} hint={`GA4 ${SESSION_NAME[ch]} sessions ÷ ${CHANNEL_LABEL[ch]} clicks`}>
                <Legend items={[
                  { label: 'Daily ratio', color: CHANNEL_COLOR[ch] },
                  { label: `Warn < ${pct(th[ch].warn, 0)}`, color: C.warn, dashed: true },
                  { label: `Critical < ${pct(th[ch].critical, 0)}`, color: C.crit, dashed: true },
                  ...(ranges.length ? [{ label: 'Alert window', color: C.crit, shade: true }] : []),
                ]} />
                <TimeChart ariaLabel={`Daily ${CHANNEL_LABEL[ch]} click-to-session ratio with warning and critical thresholds`} data={data}
                  series={[{ key: 'ratio', label: 'Sessions / clicks', color: CHANNEL_COLOR[ch] }]} fmt={(v) => pct(v, 0)} axisFmt={(v) => pct(v, 0)}
                  domain={[0, (m: number) => Math.max(1.2, Math.ceil(m * 10) / 10)]} ranges={ranges}
                  refLines={[{ y: th[ch].warn, label: 'Warn', color: C.warn }, { y: th[ch].critical, label: 'Critical', color: C.crit }]} height={260} />
              </Section>
            );
          })}
        </div>
      )}
      <Section title="Month summary"><div className="-mx-4 -my-4"><DataTable rows={sumRows} columns={cols} rowKey={(r) => r.ch} caption="Reconciliation summary" /></div></Section>
    </>
  );
}
