import type { AxisDomain } from "recharts/types/util/types";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { dateLong, dateShort } from '../lib/format';

export const C = {
  s1: 'var(--s1)', s2: 'var(--s2)', s3: 'var(--s3)', s4: 'var(--s4)', s5: 'var(--s5)', s6: 'var(--s6)',
  grid: 'var(--grid)', crit: 'rgb(var(--crit))', warn: 'rgb(var(--warn))', good: 'rgb(var(--good))',
  ink3: 'rgb(var(--ink-3))', accent: 'rgb(var(--accent))',
};
export const CHANNEL_COLOR: Record<string, string> = { google_ads: C.s1, meta_ads: C.s2, total: C.s1 };

export interface Series { key: string; label: string; color: string; dashed?: boolean }
export interface Range { start: string; end: string; severity: string; label?: string }
export interface RefLine { y: number; label: string; color: string }

export function Legend({ items }: { items: { label: string; color: string; dashed?: boolean; shade?: boolean }[] }) {
  return (
    <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          {i.shade ? (
            <span className="h-3 w-3 rounded-sm border border-dashed" style={{ background: `color-mix(in srgb, ${i.color} 14%, transparent)`, borderColor: i.color }} />
          ) : (
            <svg width="14" height="8" aria-hidden><line x1="0" x2="14" y1="4" y2="4" stroke={i.color} strokeWidth="2" strokeLinecap="round" strokeDasharray={i.dashed ? '3 3' : undefined} /></svg>
          )}
          {i.label}
        </li>
      ))}
    </ul>
  );
}

type TipEntry = { dataKey?: string | number; value?: number | string; color?: string; name?: string };
function Tip({ active, payload, label, series, fmt, total }: { active?: boolean; payload?: TipEntry[]; label?: string; series: Series[]; fmt: (v: number) => string; total?: boolean }) {
  if (!active || !payload?.length || !label) return null;
  const rows = series.map((s) => ({ s, v: payload.find((p) => p.dataKey === s.key)?.value as number | undefined })).filter((r) => r.v != null);
  const sum = rows.reduce((a, r) => a + (r.v ?? 0), 0);
  return (
    <div className="min-w-[150px] rounded-lg border border-line-strong bg-surface p-2.5 text-xs shadow-lg">
      <div className="mb-1.5 font-medium text-ink">{dateLong(label)}</div>
      {rows.map(({ s, v }) => (
        <div key={s.key} className="flex items-center justify-between gap-4 py-0.5">
          <span className="flex items-center gap-1.5 text-ink-2"><span className="h-2 w-2 rounded-full" style={{ background: s.color }} />{s.label}</span>
          <span className="num font-medium text-ink">{fmt(v as number)}</span>
        </div>
      ))}
      {total && rows.length > 1 && (
        <div className="mt-1 flex justify-between border-t border-line pt-1 font-medium"><span className="text-ink-2">Total</span><span className="num">{fmt(sum)}</span></div>
      )}
    </div>
  );
}

function clampRange(r: Range, dates: string[]) {
  const a = dates.find((d) => d >= r.start);
  const idx = dates.filter((d) => d <= r.end).length - 1;
  if (!a || idx < 0) return null;
  let b = dates[idx];
  if (a === b && dates[idx + 1]) b = dates[idx + 1];
  return { x1: a, x2: b };
}

export function TimeChart({ data, series, fmt, axisFmt, stack, ranges = [], refLines = [], height = 240, domain, ariaLabel, total }: {
  data: { date: string; [k: string]: number | string | null }[]; series: Series[]; fmt: (v: number) => string; axisFmt?: (v: number) => string;
  stack?: boolean; ranges?: Range[]; refLines?: RefLine[]; height?: number; domain?: AxisDomain; ariaLabel: string; total?: boolean;
}) {
  const dates = data.map((d) => d.date);
  const Chart = stack ? AreaChart : LineChart;
  const common = (
    <>
      <CartesianGrid vertical={false} stroke={C.grid} />
      <XAxis dataKey="date" tickFormatter={dateShort} tickLine={false} axisLine={{ stroke: C.grid }} minTickGap={28} tickMargin={8} />
      <YAxis tickFormatter={axisFmt ?? fmt} tickLine={false} axisLine={false} width={52} domain={domain} />
      <Tooltip content={<Tip series={series} fmt={fmt} total={total ?? stack} />} cursor={{ stroke: 'rgb(var(--ink-3))', strokeWidth: 1, strokeDasharray: '3 3' }} />
      {ranges.map((r, i) => {
        const c = clampRange(r, dates);
        if (!c) return null;
        const col = r.severity === 'critical' ? C.crit : C.warn;
        return (
          <ReferenceArea key={i} {...c} fill={col} fillOpacity={0.1} stroke={col} strokeOpacity={0.45} strokeDasharray="3 3" ifOverflow="visible"
            label={{ value: r.label ?? 'Alert', position: 'insideTopLeft', fill: col, fontSize: 11, fontWeight: 600 }} />
        );
      })}
      {refLines.map((l) => (
        <ReferenceLine key={l.label} y={l.y} stroke={l.color} strokeDasharray="5 4" strokeWidth={1.25}
          label={{ value: l.label, position: 'insideBottomRight', fill: l.color, fontSize: 11 }} />
      ))}
    </>
  );
  return (
    <div role="img" aria-label={ariaLabel} style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <Chart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          {common}
          {series.map((s) =>
            stack ? (
              <Area key={s.key} dataKey={s.key} name={s.label} stackId="a" type="monotone" stroke={s.color} strokeWidth={1.5} fill={s.color} fillOpacity={0.75} isAnimationActive={false} />
            ) : (
              <Line key={s.key} dataKey={s.key} name={s.label} type="monotone" stroke={s.color} strokeWidth={2} strokeDasharray={s.dashed ? '4 4' : undefined} dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: 'rgb(var(--surface))' }} isAnimationActive={false} connectNulls={false} />
            ))}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}

export function Sparkline({ data, color = C.s1, label }: { data: { v: number }[]; color?: string; label: string }) {
  return (
    <div role="img" aria-label={label} className="h-8 w-28">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
          <Area dataKey="v" type="monotone" stroke={color} strokeWidth={1.5} fill={color} fillOpacity={0.12} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
