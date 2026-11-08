# Agency reporting web app

Static React app (Vite + TypeScript + Tailwind 3 + Recharts + HashRouter). No backend: it reads JSON from `public/data/`,
produced by the Python pipeline (contract: `../docs/WEB_SPEC.md`).

```bash
# from the repo root, generate the data
uv run agency-pipeline export-web

cd web
npm ci
npm run dev        # http://localhost:5173
npm run build      # type-check + production build into web/dist (base './', works on a GitHub Pages subpath)
npm run preview    # serve dist on :4173
```

Routes: `#/` portfolio, `#/clients/:id?tab=overview|paid|campaigns|website|seo|data-quality`, `#/alerts`,
`#/report/:id/:month` (white-label, print to PDF). `?month=YYYY-MM` is shared across screens. Cmd/Ctrl+K opens the client switcher.

Layout: `src/lib` (types, fetch hooks with cache, formatting, metrics), `src/components` (shell, UI kit, charts), `src/pages`.
Theme tokens live in `src/index.css`; the agency accent colour comes from `manifest.agency.primary_color` at runtime.
