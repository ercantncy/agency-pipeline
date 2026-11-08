import { Link, useParams, useSearchParams } from 'react-router-dom';
import { FileText } from 'lucide-react';
import { useLink, useMonth } from '../lib/app';
import { useClient } from '../lib/data';
import { monthLabel } from '../lib/format';
import { alertsFor, healthOf, SCENARIO_LABEL } from '../lib/metrics';
import { ErrorState, HealthBadge, PageHeader, PageSkeleton, Tabs } from '../components/ui';
import OverviewTab from './client/OverviewTab';
import PaidTab from './client/PaidTab';
import CampaignsTab from './client/CampaignsTab';
import WebsiteTab from './client/WebsiteTab';
import SeoTab from './client/SeoTab';
import DataQualityTab from './client/DataQualityTab';

const TABS = [
  { id: 'overview', label: 'Overview' }, { id: 'paid', label: 'Paid media' }, { id: 'campaigns', label: 'Campaigns' },
  { id: 'website', label: 'Website' }, { id: 'seo', label: 'SEO' }, { id: 'data-quality', label: 'Data quality' },
] as const;
type TabId = (typeof TABS)[number]['id'];

export default function Client() {
  const { clientId } = useParams();
  const [month] = useMonth();
  const link = useLink();
  const [sp, setSp] = useSearchParams();
  const { data: c, error, loading } = useClient(clientId);
  const q = sp.get('tab');
  const tab: TabId = TABS.some((t) => t.id === q) ? (q as TabId) : 'overview';
  if (loading) return <PageSkeleton />;
  if (error || !c) return <ErrorState message={error ? `Unknown client or missing data (${error}).` : 'No data.'} />;
  const al = alertsFor(c, month);
  const props = { c, month };
  return (
    <>
      <PageHeader
        eyebrow={<Link to={link('/')} className="hover:underline">Portfolio</Link>}
        title={<span className="flex items-center gap-3">{c.client.client_name}<HealthBadge health={healthOf(al)} count={al.length} /></span>}
        subtitle={`${monthLabel(month, true)} · ${SCENARIO_LABEL[c.client.scenario] ?? c.client.scenario} · ${c.client.currency}`}
        actions={<Link to={`/report/${c.client.client_id}/${month}`} className="btn"><FileText size={14} aria-hidden />Client report</Link>}
      />
      <Tabs label="Client sections" tabs={[...TABS]} value={tab} onChange={(t) => setSp((p) => { const n = new URLSearchParams(p); n.set('tab', t); return n; }, { replace: true })} />
      <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${tab}`} className="space-y-6">
        {tab === 'overview' && <OverviewTab {...props} />}
        {tab === 'paid' && <PaidTab {...props} />}
        {tab === 'campaigns' && <CampaignsTab {...props} />}
        {tab === 'website' && <WebsiteTab {...props} />}
        {tab === 'seo' && <SeoTab {...props} />}
        {tab === 'data-quality' && <DataQualityTab {...props} />}
      </div>
    </>
  );
}
