import type { Alert, ClientData, MonthlyChannel, MonthlyRow } from './types';
import { monthOf } from './format';

export type Health = 'critical' | 'warn' | 'healthy';

export const rowFor = (c: ClientData, month: string, ch: MonthlyChannel = 'total_paid'): MonthlyRow | undefined =>
  c.monthly.find((r) => r.month === month && r.channel === ch);

export const alertsFor = (c: ClientData, month: string): Alert[] => c.months[month]?.alerts ?? [];

export function healthOf(alerts: { severity: string }[]): Health {
  if (alerts.some((a) => a.severity === 'critical')) return 'critical';
  if (alerts.length) return 'warn';
  return 'healthy';
}

export const inMonth = <T extends { date: string }>(rows: T[], month: string) =>
  rows.filter((r) => monthOf(r.date) === month);

export function monthEnd(month: string) {
  const [y, m] = month.split('-').map(Number);
  return new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
}

/** Dedupe alerts that share a date range (for chart shading). */
export function alertRanges(alerts: Alert[]) {
  const map = new Map<string, { start: string; end: string; severity: string }>();
  for (const a of alerts) {
    const k = a.start_date + a.end_date;
    const cur = map.get(k);
    if (!cur || a.severity === 'critical') map.set(k, { start: a.start_date, end: a.end_date, severity: a.severity });
  }
  return [...map.values()];
}

export function sum<T>(rows: T[], f: (r: T) => number) {
  return rows.reduce((a, r) => a + f(r), 0);
}

/** Pivot paid_daily to one row per date with per-channel + total values. */
export function paidSeries(c: ClientData, month: string, metric: 'spend' | 'clicks' | 'conversions' | 'impressions') {
  const by = new Map<string, { date: string; google_ads: number; meta_ads: number; total: number }>();
  for (const r of c.paid_daily) {
    if (monthOf(r.date) !== month) continue;
    const e = by.get(r.date) ?? { date: r.date, google_ads: 0, meta_ads: 0, total: 0 };
    e[r.channel] += r[metric];
    e.total += r[metric];
    by.set(r.date, e);
  }
  return [...by.values()].sort((a, b) => a.date.localeCompare(b.date));
}

/** Total paid spend for the 30 days ending at the month end. */
export function spendLast30(c: ClientData, month: string) {
  const end = monthEnd(month);
  const by = new Map<string, number>();
  for (const r of c.paid_daily) if (r.date <= end) by.set(r.date, (by.get(r.date) ?? 0) + r.spend);
  return [...by.entries()].sort((a, b) => a[0].localeCompare(b[0])).slice(-30).map(([date, v]) => ({ date, v }));
}

export const GBP_TO_USD = 1.27; // indicative, for portfolio roll-ups only
export const toUsd = (v: number, cur: string) => (cur === 'GBP' ? v * GBP_TO_USD : v);

export const SCENARIO_LABEL: Record<string, string> = {
  healthy: 'Healthy',
  broken_autotagging: 'Auto-tagging broken',
  tracking_outage: 'Tracking outage',
};
