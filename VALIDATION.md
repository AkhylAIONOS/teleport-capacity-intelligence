# PDF-aligned MVP revision validation

Validated October 1, 2026; Python 3.11, Node 24. The existing project, adapter, optimizer and other navigation pages were preserved.

- Reference review: PDF pages 4 and 5 rendered and visually inspected. Page 4 governs table-first layout and three lower visuals; page 5 governs KPI and teal/light styling.
- Backend: `python -m pytest -q` — **113 passed**, including all existing cases plus demo 5–10% calibration, already-optimal share, lane/month heatmap reconciliation and filtering, API cells, and an uncapped 50% synthetic real-data calculation. One Starlette TestClient dependency deprecation warning; no failed tests.
- Frontend: `npm test` — **23 passed**, covering prior functional flows with the retired modal test adapted to the dock, plus A–J flows, API/empty/malformed responses, error-boundary recovery, scope changes, collapse/history persistence, retained pages, Overview ordering and date presentation.
- Frontend: `npm run build` — TypeScript and Vite production build **passed**.
- Live `python scripts/smoke_api.py` — **passed**, through the actual frontend proxy and refreshed CSV-backed backend. Verifies filtered dashboard/AI agreement, heatmap totals and periods, June $300 actions, shipment detail, and top-lane → Why? → Show me those shipments context.
- Regenerated demo: **2,000 shipments**, **12,123 candidate options**, **181 fuel rows**, 12 lanes and eight carriers over January–June 2026.
- Backend-computed demo savings rate: **6.7376292589%**; this is generation calibration, not a displayed or real-data percentage cap.
- Code-level AI crash path: the old renderer read `Object.entries(result.metrics)`, `Object.keys(result.filters)`, `result.table.length`, and scope properties without runtime validation or a boundary. Missing/null response fields could throw during rendering and take down the dashboard. New normalization and an isolated boundary cover these cases; API failures show “AI Analyst could not load. Please retry.” inside the dock.
- Original browser symptom / visual browser QA: **not reproduced or inspected**. Browser discovery returned no connected browsers. The source PDF was visually reviewed, but component tests do not prove pixel/layout fidelity. No exact original click-failure stack trace is available.
- Optional live OpenAI: no paid call made; original mocked provider safety/failure tests still pass.

Servers were refreshed and left running at http://127.0.0.1:5173 and http://127.0.0.1:8000. Reload the dashboard to pick up the latest UI; use Retry if an earlier tab cached a request failure during the backend restart.
