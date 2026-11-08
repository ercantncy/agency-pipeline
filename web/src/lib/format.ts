const cache = new Map<string, Intl.NumberFormat>();
function nf(key: string, locale: string, opts: Intl.NumberFormatOptions) {
  const k = key + locale + JSON.stringify(opts);
  let f = cache.get(k);
  if (!f) cache.set(k, (f = new Intl.NumberFormat(locale, opts)));
  return f;
}
const localeFor = (cur: string) => (cur === 'GBP' ? 'en-GB' : 'en-US');
const NA = '—';

export function money(v: number | null | undefined, cur: string, o: { decimals?: number; compact?: boolean } = {}) {
  if (v == null || Number.isNaN(v)) return NA;
  const compact = o.compact && Math.abs(v) >= 10000;
  return nf('c' + cur, localeFor(cur), {
    style: 'currency', currency: cur,
    notation: compact ? 'compact' : 'standard',
    minimumFractionDigits: o.decimals ?? 0, maximumFractionDigits: o.decimals ?? (compact ? 1 : 0),
  }).format(v);
}
export const money2 = (v: number | null | undefined, cur: string) => money(v, cur, { decimals: 2 });
export function int(v: number | null | undefined) {
  return v == null ? NA : nf('i', 'en-US', { maximumFractionDigits: 0 }).format(v);
}
export function compact(v: number | null | undefined) {
  return v == null ? NA : nf('k', 'en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(v);
}
export function pct(v: number | null | undefined, d = 1) {
  return v == null ? NA : nf('p', 'en-US', { style: 'percent', minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
}
export function signedPct(v: number | null | undefined, d = 1) {
  if (v == null) return NA;
  const s = pct(Math.abs(v), d);
  return (v > 0 ? '+' : v < 0 ? '−' : '') + s;
}
export function ratio(v: number | null | undefined, d = 2) {
  return v == null || v === 0 ? NA : nf('r', 'en-US', { minimumFractionDigits: d, maximumFractionDigits: d }).format(v) + '×';
}
export function num1(v: number | null | undefined) {
  return v == null ? NA : nf('n1', 'en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(v);
}
const parse = (iso: string) => new Date(iso.length === 7 ? iso + '-01T00:00:00Z' : iso + 'T00:00:00Z');
export function dateShort(iso: string) {
  return parse(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}
export function dateLong(iso: string) {
  return parse(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });
}
export function monthLabel(m: string, long = false) {
  return parse(m).toLocaleDateString('en-US', { month: long ? 'long' : 'short', year: 'numeric', timeZone: 'UTC' });
}
export function dateRange(a: string, b: string) {
  return a === b ? dateLong(a) : `${dateShort(a)} – ${dateLong(b)}`;
}
export function daysBetween(a: string, b: string) {
  return Math.round((parse(b).getTime() - parse(a).getTime()) / 864e5) + 1;
}
export const monthOf = (d: string) => d.slice(0, 7);
export function prevMonth(m: string) {
  const [y, mo] = m.split('-').map(Number);
  const d = new Date(Date.UTC(y, mo - 2, 1));
  return d.toISOString().slice(0, 7);
}
export const CHANNEL_LABEL: Record<string, string> = {
  google_ads: 'Google Ads', meta_ads: 'Meta Ads', total_paid: 'All paid',
};
export const CHECK_LABEL = (c: string) =>
  c.replace(/_/g, ' ').replace(/^./, (x) => x.toUpperCase());
export const GROUP_LABEL = (g: string) =>
  g.replace(/_/g, ' ').replace(/\b\w/g, (x) => x.toUpperCase());
