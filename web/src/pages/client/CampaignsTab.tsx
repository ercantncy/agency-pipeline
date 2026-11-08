import { CHANNEL_LABEL, int, money, pct, ratio } from '../../lib/format';
import type { CampaignMonthly, Channel } from '../../lib/types';
import { sum } from '../../lib/metrics';
import { C } from '../../components/charts';
import { DataTable, EmptyState, Section, type Column } from '../../components/ui';
import type { TabProps } from './shared';

export default function CampaignsTab({ c, month }: TabProps) {
  const cur = c.client.currency;
  return (
    <>
      {(['google_ads', 'meta_ads'] as Channel[]).map((ch) => {
        const rows = c.campaigns_monthly.filter((r) => r.month === month && r.channel === ch);
        const spend = sum(rows, (r) => r.spend);
        const cols: Column<CampaignMonthly>[] = [
          { key: 'n', label: 'Campaign', sort: (r) => r.campaign_name, render: (r) => <span className="font-medium">{r.campaign_name}</span> },
          { key: 'sp', label: 'Spend', align: 'right', sort: (r) => r.spend, render: (r) => money(r.spend, cur) },
          { key: 'sh', label: '% of spend', align: 'right', sort: (r) => r.spend, render: (r) => pct(spend ? r.spend / spend : null, 0) },
          { key: 'im', label: 'Impr.', align: 'right', sort: (r) => r.impressions, render: (r) => int(r.impressions) },
          { key: 'cl', label: 'Clicks', align: 'right', sort: (r) => r.clicks, render: (r) => int(r.clicks) },
          { key: 'ctr', label: 'CTR', align: 'right', sort: (r) => (r.impressions ? r.clicks / r.impressions : null), render: (r) => pct(r.impressions ? r.clicks / r.impressions : null, 2) },
          { key: 'cv', label: 'Conv.', align: 'right', sort: (r) => r.conversions, render: (r) => int(Math.round(r.conversions)) },
          { key: 'cpa', label: 'CPA', align: 'right', sort: (r) => (r.conversions ? r.spend / r.conversions : null), render: (r) => money(r.conversions ? r.spend / r.conversions : null, cur, { decimals: 2 }) },
          { key: 'roas', label: 'ROAS', align: 'right', sort: (r) => (r.spend ? r.conversion_value / r.spend : null), render: (r) => ratio(r.spend ? r.conversion_value / r.spend : null) },
        ];
        const tc = sum(rows, (r) => r.conversions);
        const foot = rows.length ? (
          <tr className="border-t border-line-strong bg-subtle/50 font-medium">
            <td className="td">Total</td><td className="td num text-right">{money(spend, cur)}</td><td className="td num text-right">100%</td>
            <td className="td num text-right">{int(sum(rows, (r) => r.impressions))}</td><td className="td num text-right">{int(sum(rows, (r) => r.clicks))}</td><td className="td" />
            <td className="td num text-right">{int(Math.round(tc))}</td><td className="td num text-right">{money(tc ? spend / tc : null, cur, { decimals: 2 })}</td>
            <td className="td num text-right">{ratio(spend ? sum(rows, (r) => r.conversion_value) / spend : null)}</td>
          </tr>
        ) : undefined;
        return (
          <Section key={ch} title={<span className="inline-flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: ch === 'google_ads' ? C.s1 : C.s2 }} />{CHANNEL_LABEL[ch]}</span>}
            hint={`${rows.length} campaigns · click a column to sort`}>
            <div className="-mx-4 -my-4">
              <DataTable rows={rows} columns={cols} rowKey={(r) => r.campaign_id} defaultSort="sp" caption={`${CHANNEL_LABEL[ch]} campaigns`} footer={foot}
                empty={<EmptyState title="No campaigns ran this month" />} />
            </div>
          </Section>
        );
      })}
    </>
  );
}
