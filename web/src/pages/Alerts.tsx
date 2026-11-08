import { useMemo, useState } from 'react';
import { CircleCheck } from 'lucide-react';
import { useApp, useLink, useMonth } from '../lib/app';
import { useClients } from '../lib/data';
import { CHECK_LABEL, monthLabel } from '../lib/format';
import { alertsFor } from '../lib/metrics';
import AlertCard from '../components/AlertCard';
import { EmptyState, ErrorState, PageHeader, PageSkeleton } from '../components/ui';

const sel = 'h-8 rounded-md border border-line-strong bg-surface px-2 text-sm';

export default function Alerts() {
  const mf = useApp();
  const [month] = useMonth();
  const link = useLink();
  const { data, error, loading } = useClients(mf.clients.map((c) => c.client_id));
  const [sev, setSev] = useState('all');
  const [check, setCheck] = useState('all');
  const [client, setClient] = useState('all');
  const all = useMemo(() => data ? mf.clients.flatMap((m) => alertsFor(data[m.client_id], month).map((a) => ({ a, name: m.client_name }))) : [], [data, mf, month]);
  if (loading) return <PageSkeleton />;
  if (error) return <ErrorState message={error} />;
  const checks = [...new Set(all.map((x) => x.a.check))];
  const shown = all.filter((x) => (sev === 'all' || x.a.severity === sev) && (check === 'all' || x.a.check === check) && (client === 'all' || x.a.client_id === client))
    .sort((x, y) => (y.a.severity === 'critical' ? 1 : 0) - (x.a.severity === 'critical' ? 1 : 0) || y.a.end_date.localeCompare(x.a.end_date));
  const crit = all.filter((x) => x.a.severity === 'critical').length;
  return (
    <>
      <PageHeader title="Alerts" subtitle={`${monthLabel(month, true)} · ${all.length} total, ${crit} critical`} />
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filters">
        <select className={sel} aria-label="Severity" value={sev} onChange={(e) => setSev(e.target.value)}>
          <option value="all">All severities</option><option value="critical">Critical</option><option value="warn">Warning</option></select>
        <select className={sel} aria-label="Check type" value={check} onChange={(e) => setCheck(e.target.value)}>
          <option value="all">All checks</option>{checks.map((c) => <option key={c} value={c}>{CHECK_LABEL(c)}</option>)}</select>
        <select className={sel} aria-label="Client" value={client} onChange={(e) => setClient(e.target.value)}>
          <option value="all">All clients</option>{mf.clients.map((c) => <option key={c.client_id} value={c.client_id}>{c.client_name}</option>)}</select>
      </div>
      {shown.length ? (
        <div className="flex flex-col gap-3">
          {shown.map(({ a, name }, i) => <AlertCard key={i} alert={a} clientName={name} to={link(`/clients/${a.client_id}`, { tab: 'data-quality' })} />)}
        </div>
      ) : (
        <div className="card"><EmptyState icon={<CircleCheck size={18} aria-hidden />} title={all.length ? 'No alerts match these filters' : 'No alerts this month'}
          body={all.length ? 'Try clearing a filter.' : 'Every data check passed for every client.'} /></div>
      )}
    </>
  );
}
