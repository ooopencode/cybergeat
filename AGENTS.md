# AGENTS.md

Pure-frontend lunch lottery on GitHub Pages: `index.html` + `candidates.json`. No backend at runtime.

## Run / Deploy

```bash
pip install requests
$env:AMAP_API_KEY="xxx"; python scripts/fetch_lunch.py  # regen candidates.json
python -m http.server 8000  # local preview: http://localhost:8000
```
Push to GitHub → Settings → Pages → Deploy from branch `/ (root)` → `https://<user>.github.io/<repo>/`.
Secrets: repo Settings → Secrets → `AMAP_API_KEY` (Web服务 key, never in frontend).

## Architecture

- `index.html` (root, Pages entry) — Leaflet + **AMap raster tiles (GCJ02)** via bootcdn (OSM/unpkg are blocked on China mobile networks). Converts `candidates.json` WGS84→GCJ02 in-page (`toGcjLatLng`, same math as fetch script). `换一家` = local re-pick, `刷新数据` = re-fetch json.
- `candidates.json` (root, committed) — `{"updated_at" (Beijing), "center": {WGS84}, "count", "results": [...]}`. Generated, but must be committed for Pages.
- `scripts/fetch_lunch.py` — AMap `place/around` (`keywords=美食`, `types=050000`, `RADIUS=800`, 3 pages x 25). Fixed `CENTER_GCJ02=(114.061104,22.573133)` = 深圳新一代产业园. Converts POIs GCJ02→WGS84 for Leaflet.
- `.github/workflows/refresh-lunch.yml` — workdays 10:00-14:00 Beijing every 30min + manual + push trigger; commits refreshed `candidates.json`.

## Gotchas

- **Key only in 2 places:** Actions secret `AMAP_API_KEY` + local env. Never inline it into `index.html`/`candidates.json`. Script exits 1 if missing.
- **Single source of truth is GCJ02:** `CENTER_GCJ02` in fetch script; frontend coordinates are pre-converted WGS84. No `wgs84_to_gcj02` anywhere.
- **No fake data:** missing/list `biz_ext.rating/cost` → `None`, frontend shows `暂无评分/价格暂无`.
- `distance` is int meters; `id` is AMap POI id; empty-name POIs skipped.
