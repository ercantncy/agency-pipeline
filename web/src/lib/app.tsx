import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useManifest } from './data';
import type { Manifest } from './types';

const Ctx = createContext<{ manifest: Manifest } | null>(null);
export const useApp = () => useContext(Ctx)!.manifest;

function hexToRgb(hex: string) {
  const m = /^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(hex);
  return m ? `${parseInt(m[1], 16)} ${parseInt(m[2], 16)} ${parseInt(m[3], 16)}` : null;
}

export function applyAccent(hex: string) {
  const rgb = hexToRgb(hex);
  if (rgb) document.documentElement.style.setProperty('--accent', rgb);
}

export function AppProvider({ children }: { children: ReactNode }) {
  const { data, error, loading } = useManifest();
  useEffect(() => { if (data) { applyAccent(data.agency.primary_color); document.title = `${data.agency.name} · Reporting`; } }, [data]);
  if (loading) return <div className="grid min-h-screen place-items-center text-sm text-ink-3" role="status">Loading workspace…</div>;
  if (error || !data)
    return (
      <div className="grid min-h-screen place-items-center p-6">
        <div className="card max-w-md p-6 text-center">
          <h1 className="text-base font-semibold">Couldn’t load data</h1>
          <p className="mt-1 text-sm text-ink-2">{error ?? 'manifest.json is missing.'} Run <code className="rounded bg-subtle px-1">agency-pipeline export-web</code> and reload.</p>
        </div>
      </div>
    );
  return <Ctx.Provider value={{ manifest: data }}>{children}</Ctx.Provider>;
}

/** Selected month, persisted in the URL as ?month= */
export function useMonth(): [string, (m: string) => void] {
  const manifest = useApp();
  const [sp, setSp] = useSearchParams();
  const q = sp.get('month');
  const month = q && manifest.months.includes(q) ? q : manifest.default_month;
  const set = useCallback(
    (m: string) => setSp((p) => { const n = new URLSearchParams(p); n.set('month', m); return n; }, { replace: true }),
    [setSp],
  );
  return [month, set];
}

/** Build an in-app link that keeps the selected month. */
export function useLink() {
  const [month] = useMonth();
  return useCallback((path: string, params: Record<string, string> = {}) => {
    const p = new URLSearchParams({ ...params, month });
    return `${path}?${p.toString()}`;
  }, [month]);
}

export function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    (document.documentElement.dataset.theme as 'light' | 'dark') || 'light');
  const toggle = useCallback(() => {
    setTheme((t) => {
      const n = t === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = n;
      try { localStorage.setItem('theme', n); } catch { /* ignore */ }
      return n;
    });
  }, []);
  return useMemo(() => ({ theme, toggle }), [theme, toggle]);
}
