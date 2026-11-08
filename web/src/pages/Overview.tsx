import { Link } from 'react-router-dom';
import { ArrowRight, CircleCheck } from 'lucide-react';
import { useApp, useLink, useMonth } from '../lib/app';
import { useClients } from '../lib/data';
import { int, money, monthLabel, prevMonth, ratio, signedPct } from '../lib/format';
import { alertsFor, healthOf, rowFor, spendLast30, toUsd, SCENARIO_LABEL, GBP_TO_USD } from '../lib/metrics';
import type { ClientData } from '../lib/types';
import AlertCard from '../components/AlertCard';
import { Sparkline } from '../components/charts';
import { DataTable, Delta, EmptyState, ErrorState, HealthBadge, KpiCard, PageHeader, PageSkeleton, Section, type Column } from '../components/ui';

interface Row { c: ClientData; spend?: number; conv?: number; cpa: number | null; roas: number | null; spendMom: number | null; cpaMom: number | null; health: ReturnType<typeof healthOf>; nAlerts: number }

export default function Overview() {
  const mf = useApp();
  const [month] = useMonth();
  const link = useLink();
  const { data, error, loading } = useClients(mf.clients.map((c) => c.client_id));
  if (loading) return <PageSkeleton />;
  if (error || !data) return <ErrorState message={error ?? 'No data'} />;

  const clients = mf.clients.map((m) => data[m.client_id]);
  const pm = prevMonth(month);
  const agg = (mo: string) => {
    let spend = 0, conv = 0;
    for (const c of clients) { const r = rowFor(c, mo); if (r) { spend += toUsd(r.spend, c.client.currency); conv += r.conversions; } }
    return { spend, conv, cpa: conv ? spend / conv : null };
  };
  const cur = agg(month), prev = agg(pm);
  const hasPrev = clients.some((c) => rowFor(c, pm));
  const mom = (a: number | null, b: number | null) => (hasPrev && a != null && b ? a / b - 1 : null);
  const allAlerts = clients.flatMap((c) => alertsFor(c, month).map((a) => ({ a, c })));
  const critical = allAlerts.filter((x) => x.a.severity === 'critical');
  const critClients = new Set(critical.map((x) => x.a.client_id)).size;
  const mixed = new Set(clients.map((c) => c.client.currency)).size > 1;

  const rows: Row[] = clients.map((c) => {
    const r = rowFor(c, month); const al = alertsFor(c, month);
    return { c, spend: r?.spend, conv: r?.conversions, cpa: r?.cpa ?? null, roas: r?.roas ?? null, spendMom: r?.spend_mom_pct ?? null, cpaMom: r?.cpa_mom_pct ?? null, health: healthOf(al), nAlerts: al.length };
  });
  const sevOrder = { critical: 0, warn: 1, healthy: 2 };
  const cols: Column<Row>[] = [
    { key: 'name', label: 'Client', sort: (r) => r.c.client.client_name, render: (r) => (
      <Link to={link(`/clients/${r.c.client.client_id}`)} className="group block">
        <div className="whitespace-nowrap font-medium group-hover:underline">{r.c.client.client_name}</div>
        <div className="whitespace-nowrap text-xs text-ink-3">{SCENARIO_LABEL[r.c.client.scenario] ?? r.c.client.scenario} · {r.c.client.currency}</div>
      </Link>) },
    { key: 'health', label: 'Health', sort: (r) => sevOrder[r.health], render: (r) => <HealthBadge health={r.health} count={r.nAlerts} /> },
    { key: 'spend', label: 'Spend', align: 'right', sort: (r) => r.spend ?? null, render: (r) => money(r.spend, r.c.client.currency) },
    { key: 'smom', label: 'Spend MoM', align: 'right', sort: (r) => r.spendMom, render: (r) => <span className="text-ink-2">{signedPct(r.spendMom)}</span> },
    { key: 'conv', label: 'Conv.', align: 'right', sort: (r) => r.conv ?? null, render: (r) => int(r.conv) },
    { key: 'cpa', label: 'CPA', align: 'right', sort: (r) => r.cpa, render: (r) => money(r.cpa, r.c.client.currency, { decimals: 2 }) },
    { key: 'cmom', label: 'CPA MoM', align: 'right', sort: (r) => r.cpaMom, render: (r) => <Delta value={r.cpaMom} good="down" label="" /> },
    { key: 'roas', label: 'ROAS', align: 'right', sort: (r) => r.roas, render: (r) => ratio(r.roas) },
    { key: 'spark', label: '30-day spend', render: (r) => <Sparkline data={spendLast30(r.c, month)} label={`30-day spend trend for ${r.c.client.client_name}`} /> },
  ];
  const feed = [...allAlerts].sort((x, y) => (y.a.severity === 'critical' ? 1 : 0) - (x.a.severity === 'critical' ? 1 : 0) || y.a.end_date.localeCompare(x.a.end_date)).slice(0, 4);

  return (
    <>
      <PageHeader title="Portfolio overview" subtitle={`${monthLabel(month, true)} · ${clients.length} clients`} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={mixed ? 'Total spend (USD equiv.)' : 'Total spend'} value={money(cur.spend, 'USD')} delta={mom(cur.spend, prev.spend)} good="none" />
        <KpiCard label="Conversions" value={int(Math.round(cur.conv))} delta={mom(cur.conv, prev.conv)} good="up" />
        <KpiCard label="Blended CPA" value={money(cur.cpa, 'USD', { decimals: 2 })} delta={mom(cur.cpa, prev.cpa)} good="down" />
        <KpiCard label="Open critical alerts" value={critical.length}
          sub={<span className="text-xs text-ink-3">{critical.length ? `across ${critClients} client${critClients > 1 ? 's' : ''}` : 'All clear this month'}</span>} />
      </div>
      {mixed && <p className="mt-2 text-xs text-ink-3">Portfolio totals convert GBP to USD at an indicative {GBP_TO_USD} for roll-up only; client views use their own currency.</p>}

      <div className="mt-6 space-y-6">
        <Section title="Clients" hint="Sorted by health by default so problems surface first.">
          <div className="-mx-4 -my-4">
            <DataTable rows={rows} columns={cols} rowKey={(r) => r.c.client.client_id} defaultSort="health" defaultDir="asc" caption="Client performance this month" />
          </div>
        </Section>
        <Section title="Latest alerts" actions={<Link to={link('/alerts')} className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline">View all<ArrowRight size={12} aria-hidden /></Link>}>
          {feed.length ? (
            <div className="grid gap-3 lg:grid-cols-2">
              {feed.map(({ a, c }, i) => <AlertCard key={i} alert={a} clientName={c.client.client_name} to={link(`/clients/${c.client.client_id}`, { tab: 'data-quality' })} />)}
            </div>
          ) : <EmptyState icon={<CircleCheck size={18} aria-hidden />} title="No alerts this month" body="Every data check passed for every client." />}
        </Section>
      </div>
    </>
  );
}
