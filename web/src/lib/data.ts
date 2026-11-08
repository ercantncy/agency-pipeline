import { useEffect, useState } from 'react';
import type { ClientData, Manifest } from './types';

type State<T> = { data?: T; error?: string; loading: boolean };
const cache = new Map<string, Promise<unknown>>();
const resolved = new Map<string, unknown>();

function load<T>(path: string): Promise<T> {
  let p = cache.get(path) as Promise<T> | undefined;
  if (!p) {
    p = fetch(`./data/${path}`).then((r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return r.json() as Promise<T>;
    });
    p.then((d) => resolved.set(path, d), () => cache.delete(path));
    cache.set(path, p);
  }
  return p;
}

function useJson<T>(path: string | null): State<T> {
  const [st, setSt] = useState<State<T>>(() =>
    path && resolved.has(path) ? { data: resolved.get(path) as T, loading: false } : { loading: !!path });
  useEffect(() => {
    if (!path) return;
    if (resolved.has(path)) { setSt({ data: resolved.get(path) as T, loading: false }); return; }
    let live = true;
    setSt({ loading: true });
    load<T>(path).then(
      (data) => live && setSt({ data, loading: false }),
      (e: Error) => live && setSt({ error: e.message, loading: false }),
    );
    return () => { live = false; };
  }, [path]);
  return st;
}

export const useManifest = () => useJson<Manifest>('manifest.json');
export const useClient = (id: string | undefined) => useJson<ClientData>(id ? `clients/${id}.json` : null);

/** Loads several clients in parallel (cached). */
export function useClients(ids: string[]): State<Record<string, ClientData>> {
  const key = ids.join(',');
  const [st, setSt] = useState<State<Record<string, ClientData>>>({ loading: true });
  useEffect(() => {
    if (!ids.length) return;
    let live = true;
    setSt({ loading: true });
    Promise.all(ids.map((id) => load<ClientData>(`clients/${id}.json`))).then(
      (arr) => live && setSt({ loading: false, data: Object.fromEntries(arr.map((c, i) => [ids[i], c])) }),
      (e: Error) => live && setSt({ loading: false, error: e.message }),
    );
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return st;
}
