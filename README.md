# Teleport Capacity Intelligence

A local, working logistics capacity and cost backtesting MVP. **The bundled shipment-level data is public-source-calibrated synthetic data. It is not real Teleport history, carrier pricing, or commercial performance.** All monetary amounts are USD.

Explore 2,000 simulated historical shipments, 13,147 synthetic candidate options, 18 lanes, nine representative carriers, and daily fuel indices across January–June 2026. The fixed-seed generator makes the demo reproducible. Carrier names are illustrative; the generated values are not quotes from those carriers.

## Quick start (macOS/Linux)

Requires Python **3.11+**, Node **22+**, and npm. On this machine, use `python3.11`; the default `python3` is older than the required version.

From this project directory, start the backend in one terminal:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal, from the project directory:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev -- --port 5173
```

Open **http://127.0.0.1:5173**. API docs: **http://127.0.0.1:8000/docs**. Health: **http://127.0.0.1:8000/health**. No API key or database is required. The demo CSVs are already included; do not regenerate them over real data.

For another Python installation, replace `python3.11` with your Python 3.11+ executable. For a remote frontend, set `VITE_API_BASE_URL` to the reachable backend URL, and add the frontend origin to backend `CORS_ORIGINS`. The development proxy is not included in production assets; production hosting must route `/api` to FastAPI or use the explicit API base URL at build time.

## Implemented experience

- PDF page 4 Overview layout: compact four-KPI strip (potential savings, scored shipments, already-optimal share, average flagged saving), six-row recommendation queue, then exactly three visuals: cumulative actual/engine cost, lane × month heatmap, and actual/recommended rate mix. Page 5 supplies teal accents, light surfaces and compact card styling. Spend remains secondary; carrier analytics remains on the Carriers page.
- Global date, origin, destination, lane, actual carrier, actual rate, minimum saving, and shipment search filters. Recommended carrier filters and result-ID filters are available via the analyst and API. All analytics use the same filtered shipment set.
- Shipment table with column sorting, highest-saving sort, pagination, search, changed-decision badges, and CSV export of the **current page**.
- Accessible right-side shipment detail drawer with actual/recommended component costs, transparent candidate exclusion reasons, and a deterministic explanation.
- Dedicated Shipments, Lanes, Carriers, Backtest, and Data Quality navigation views. Lanes/carriers can filter the shipment view.
- Integrated 348px desktop AI analyst dock (320px on smaller desktops), with a persistent input, scrollable history, collapse/reopen controls, suggestions, grounded result tables and charts. On mobile it stacks below the dashboard. Filter commands update Overview in place; messages and the panel remain visible. An isolated error boundary plus runtime response validation prevent malformed API responses from blanking the dashboard.
- Loading, empty, and retryable error states. Data quality always audits the **entire raw dataset**, rather than changing with dashboard filters.

## Architecture and folder structure

```text
teleport-capacity-intelligence/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI lifecycle, CORS, routers
│   │   ├── config.py                # Paths, environment, centralized maps
│   │   ├── api/
│   │   │   ├── dashboard.py
│   │   │   ├── shipments.py
│   │   │   ├── analytics.py
│   │   │   └── ai.py
│   │   ├── models/
│   │   │   ├── analytics.py         # Filters, query/chat contracts
│   │   │   ├── shipment.py
│   │   │   └── carrier_option.py
│   │   ├── services/
│   │   │   ├── data_loader.py       # Source adapter + audit/quarantine
│   │   │   ├── optimizer.py         # Feasibility + deterministic ranking
│   │   │   ├── analytics_service.py # Shared computations
│   │   │   ├── query_router.py      # Intent/entity/context parser
│   │   │   └── ai_service.py        # Providers + grounded answer renderer
│   │   └── utils/filters.py
│   ├── data/
│   │   ├── shipments.csv
│   │   ├── carrier_options.csv
│   │   └── fuel_index.csv
│   ├── scripts/generate_demo.py
│   ├── tests/
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── column_map.example.json
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/              # Charts, table, drawer, analyst
│   │   ├── pages/Backtest.tsx
│   │   ├── hooks/useDashboard.ts
│   │   ├── services/api.ts
│   │   ├── types/index.ts
│   │   ├── test/                    # React interaction tests
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── index.html
│   └── .env.example
├── README.md
└── .gitignore
```

FastAPI loads canonical Pandas dataframes and computes the backtest once at startup. All read endpoints filter and aggregate that same immutable result. React requests those endpoints; it formats returned numbers and never computes business metrics. No unrestricted SQL is generated or executed. DuckDB is unnecessary for this dataset size. CSV loading is behind one adapter so source column mapping does not affect canonical business logic.

## Optimization and financial definitions

Each shipment is evaluated independently against its recorded candidate rows:

1. Check availability.
2. Check capacity against **both** recorded required capacity and shipment weight; understated required capacity cannot bypass the weight check.
3. Require the recorded SLA flag.
4. Require valid dates, nonnegative finite costs, complete carrier/option identity, and consistent component totals.
5. Select the lowest total landed cost; ties use earlier departure, alphabetical carrier, then option ID.
6. Compute `potential_saving = max(actual_paid - optimized_cost, 0)`.

If no feasible option exists, return `NO_FEASIBLE_ALTERNATIVE` and retain the historical carrier, rate, departure and paid amount; savings are zero. If the cheapest feasible option costs more than historical payment, optimized cost is still that actual candidate cost, with zero saving. Therefore **aggregate actual spend minus aggregate optimized spend need not equal aggregate nonnegative potential savings** on a real dataset with more expensive recommendations.

Actual paid and landed totals must match component sums to one-cent tolerance. Invalid historical shipment rows are quarantined, duplicate IDs are all excluded, and invalid candidate rows remain visible for the audit but cannot win. Required source columns missing at startup produce an explicit validation error naming the file and columns.

- Already optimal share: `(shipment_count - flagged_shipments) / shipment_count * 100`, computed in the backend. By the requested definition, this includes zero-saving historical fallbacks.
- Heatmap: backend groups potential savings, actual spend and optimized spend by lane and ISO month; intensity is the cell saving relative to the highest saving in the filtered scope. Lane click applies a lane; cell click adds the actual month boundaries. Hover/focus shows audited cost metrics.
- Actual spend: sum of `actual_paid`.
- Optimized spend: sum of selected candidate costs or historical fallback costs.
- Potential saving: sum of shipment-level nonnegative savings.
- Saving rate: potential saving / actual spend, with zero for empty/zero spend.
- Flagged shipments: positive potential saving.
- Average flagged saving: total saving / flagged count, with zero for no flagged shipments.
- Rate mix: shipment count shares; analyst also reports cargo-weight shares. Fallbacks count as retained historical decisions.
- Carrier opportunity: savings attributed to the **actual carrier** and its historical shipment mix. Recommended usage is counted across the current filtered scope.

The engine does **not** allocate shared flight capacity between shipments, infer unrecorded availability, infer business reasons for historical choices, predict future savings, or optimize flight schedules. Backtest opportunities are descriptive, not a portfolio allocation plan.

## AI analytics and supported questions

`AI_PROVIDER=mock` uses explicit deterministic intent routing. Conversation context is held in React memory and sent with each request; it survives collapsing/reopening the dock until page reload. Dashboard/heatmap filter changes synchronize lane and period context without clearing conversation history. No globally shared server conversation state is used.

Supported categories and examples:

| Category                   | Example                                                                       |
| -------------------------- | ----------------------------------------------------------------------------- |
| Overall savings            | How much could we have saved? / How much did we overspend?                    |
| Time scope                 | How much could we have saved in June? / Show savings last month.              |
| Top lanes                  | Which lane has the biggest opportunity? / Show top 5 lanes by missed savings. |
| Lane audit                 | Analyze KUL to DEL. / Why is KUL-DEL expensive?                               |
| Lane comparison            | Compare KUL-DEL and KUL-BOM.                                                  |
| Carrier metrics            | How much did we spend with Emirates? / Show performance for MASkargo.         |
| Carrier comparison         | Compare MASkargo and Emirates on KUL-DEL.                                     |
| Shipment lookup            | What was the cheapest option for TP-88213?                                    |
| Highest savings            | Show top 10 missed-saving shipments.                                          |
| Rate analysis              | Compare spot vs contract. / Where did spot beat contracted rates?             |
| Trend                      | Are savings opportunities increasing? / Compare May and June.                 |
| Summary                    | Give me a June performance summary. / What are the key findings?              |
| Filter command             | Show June shipments above $300 saving. / Show spot shipments from BOM.        |
| Recommended carrier filter | Show only MASkargo recommendations.                                           |

Month-only questions use the latest year present in the loaded data unless the user supplies a year. **Last month uses the actual current calendar**, so it will return an honest empty result if that month is absent from the historical data. Named lane codes support hyphen, `to`, slash, and arrow separators. Top-N is bounded to 50 rows.

Try the sequence: “Which lane has the biggest opportunity?” → “Why?” → “Show me those shipments.” The lane subject is preserved and the last response applies the lane to the dashboard. Shipment and comparison follow-ups are supported as well. After a top shipment list, “Show me those shipments” applies those returned IDs. Unsupported questions return: “The available dataset does not contain enough information to answer this reliably.” Cost-gap explanations describe recorded comparisons, rather than inventing the decision-maker's motivation.

`AI_PROVIDER=openai` plus `OPENAI_API_KEY` enables the optional OpenAI provider for questions the deterministic parser does not recognize. It classifies intent and extracts constrained entities only; deterministic backend tools and templates calculate and render every financial answer. API failures/refusals fall back to an unsupported answer. Known question types do not incur an LLM call. The key remains on the backend. Do not put it into any `VITE_` variable. The integration follows [official OpenAI documentation on structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Live OpenAI calls are not part of the no-key acceptance tests.

Responses contain `answer`, `intent`, computed `metrics`, `table`, `filters`, optional `chart`, `confidence`, `data_scope`, `context`, and `provider`. Filter commands are applied automatically; other result actions offer an Apply Filters button.

## Environment variables

| Variable            | Default / purpose                                                 |
| ------------------- | ----------------------------------------------------------------- |
| `DATA_DIR`          | Backend `data/`; relative paths resolve against backend directory |
| `DATA_MODE`         | `demo`; set `real` when using real imported datasets              |
| `COLUMN_MAP_FILE`   | Optional JSON mapping file; relative to backend directory         |
| `AI_PROVIDER`       | `mock` or `openai`                                                |
| `OPENAI_API_KEY`    | Backend-only optional key; absent key uses mock                   |
| `OPENAI_MODEL`      | Configurable model ID, default `gpt-4.1-mini`                     |
| `CORS_ORIGINS`      | Comma-separated frontend origins                                  |
| `VITE_API_BASE_URL` | Blank uses same-origin `/api`; Vite proxies to local backend      |

## Replace demo data with real Teleport data

1. Keep your real CSVs in a separate directory so regenerating demo data cannot overwrite them.
2. Provide `shipments.csv`, `carrier_options.csv`, and `fuel_index.csv`. Their canonical headers are listed in `app/config.py` and in the bundled CSVs. Fuel indices are loaded for extension, not used to retrospectively invent surcharges.
3. Set `DATA_DIR=/absolute/path/to/your/real-data` and `DATA_MODE=real` in `backend/.env`.
4. Copy `column_map.example.json` to a private mapping file and map **canonical internal column → actual external source column**. Set `COLUMN_MAP_FILE` to its path. Unspecified columns retain identity mappings. For example:

```json
{
  "shipments": {
    "shipment_id": "AWB_REFERENCE",
    "actual_paid": "TOTAL_PAID_USD",
    "origin": "ORIGIN_AIRPORT"
  },
  "carrier_options": {
    "total_landed_cost": "ALL_IN_OPTION_USD"
  }
}
```

5. Ensure money is in USD and weight in kg before ingestion. This MVP assumes one currency, one unit system, unique shipment IDs, and a historical candidate availability snapshot. It cannot reconstruct historical options from a current price list.
6. Use ISO dates (`YYYY-MM-DD`) and booleans `true`/`false` or `1`/`0`. Contract, Spot and Owned are the canonical rate values. Source files may contain extra columns; only mapped required columns are loaded. Empty datasets need headers.
7. Restart the backend. Loading and optimization are cached at process startup. Inspect **Data Quality** before using results: loaded vs usable counts, cost inconsistencies, missing carriers, duplicates, capacities, dates, orphan options, and missing candidate sets.

No frontend or optimization rewrite is needed for source column renaming. Mapping files cover column names; upstream transformations are still needed if the real source represents values in different units or multiple currencies. The product has no authentication or multiuser persistence; it is intended to run locally for this MVP.

## API

| Method | Endpoint                       | Purpose                                                  |
| ------ | ------------------------------ | -------------------------------------------------------- |
| GET    | `/health`                      | Startup health and usable rows                           |
| GET    | `/api/dashboard/summary`       | KPIs + backtest counters                                 |
| GET    | `/api/dashboard/trends`        | Monthly spend/savings; `cumulative=true` supported       |
| GET    | `/api/dashboard/lane-heatmap`  | Lane × month cost/savings cells and calculated intensity |
| GET    | `/api/dashboard/lanes`         | Lane rankings                                            |
| GET    | `/api/dashboard/carriers`      | Actual carrier statistics                                |
| GET    | `/api/dashboard/rate-mix`      | Actual/recommended shipment and weight mix               |
| GET    | `/api/dashboard/metadata`      | Filter values, available dates, full-data audit          |
| GET    | `/api/dashboard/provenance`    | Local source registry, field/lane provenance and manifest |
| GET    | `/api/dashboard/quality`       | Full loaded data quality audit                           |
| GET    | `/api/shipments`               | Sorted paginated filtered shipments                      |
| GET    | `/api/shipments/{shipment_id}` | Decision and candidate audit; 404 if missing             |
| POST   | `/api/analytics/query`         | Explicit allowlisted analytics tools                     |
| POST   | `/api/ai/chat`                 | NL intent, computed answer, context, actions             |

Shared query filters: `start_date`, `end_date`, `origin`, `destination`, `lane`, `carrier` (historical actual), `recommended_carrier`, `rate_type` (historical actual), `recommended_rate_type`, `min_saving`, `search`, and `shipment_ids` (JSON array in query params). Date boundaries are inclusive. Shipment-specific parameters: `page`, `page_size` (up to 100), `sort_by` (allowlisted column), `descending`. Invalid filters and sorting yield 422 responses.

```bash
curl 'http://127.0.0.1:8000/api/dashboard/summary?lane=KUL-DEL&min_saving=300'
curl 'http://127.0.0.1:8000/api/shipments/TP-88213'
curl -X POST 'http://127.0.0.1:8000/api/ai/chat' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Which lane has the biggest opportunity?","filters":{},"context":{}}'
curl -X POST 'http://127.0.0.1:8000/api/analytics/query' \
  -H 'Content-Type: application/json' \
  -d '{"intent":"TOP_LANES","limit":5,"filters":{}}'
```

## Tests and production build

Backend (from project root):

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
```

Frontend (from project root):

```bash
cd frontend
npm test
npm run build
npm run preview -- --port 4173
```

The backend suite tests feasibility exclusions, tie breaking, nonnegative savings, valid recommendations, aggregates, date/lane/carrier/rate filters, lookup, top-N, rate mix, trends, all supplied question examples, context, endpoint contracts, column remapping, data quality and empty files. Frontend component tests exercise API-driven metrics, filter refreshes, drawer transparency, analyst dashboard actions, reset and failures. Their transport fixtures are test-only and are never shipped as product data.

A real browser was unavailable in the build session, so visual browser QA has not been claimed. Backend health, frontend HTTP serving, React interactions, TypeScript compilation and production bundling were checked. The optional live OpenAI integration requires your key and was tested with mocked transport rather than a paid call.

Regenerate only the simulated files (overwrites backend `data/*.csv`):

```bash
cd backend
python scripts/generate_demo.py
```

For a live backend-through-Vite-proxy smoke check, keep both servers running and execute `python scripts/smoke_api.py` from the backend virtual environment. This checks CSV-backed values, filtered shipment rows, detail candidates, analytics endpoints, and an AI follow-up action against the actual running API.

## PDF-aligned demo revision

The included `Teleport_Capacity_Backtest_Brief.pdf` page 4 is the primary Overview layout; page 5 is styling guidance only. All four decision-support elements remain together rather than moving the table below analytics. Dates remain ISO internally and display as Jan/Feb/Mar or readable dates. Recommendation Day displays the departure weekday; the full date is available on hover and in the audit drawer.

The fixed-seed generator now uses a shared market-cost baseline per shipment and a distribution of zero/small/moderate/larger option discounts. It naturally produces an aggregate opportunity of **6.70%** (2,000 demo shipments), rather than unrelated per-carrier prices producing 32%. The 5–10% regression expectation applies to bundled generated demo data only; no metric, optimizer, real-data adapter, or UI applies a percentage cap.

The old AI rendering assumed `metrics`, `table`, `filters` and `data_scope` always existed, using unchecked `Object.entries`, `Object.keys` and property access. An incomplete response could throw a render exception with no error boundary to protect the dashboard. The new dock normalizes transport data, displays an in-chat retry for empty/error responses, and catches unexpected panel render exceptions. Exact reproduction of the original browser click failure was unavailable because the browser runtime had no connected browser; component tests verify these concrete failure paths and the replacement flow.

## DATA PROVENANCE

The committed demo is **PUBLIC-SOURCE-CALIBRATED SYNTHETIC DATA**. It is not actual
Teleport shipment history, and its savings are not Teleport financial results.

- **PUBLIC:** Teleport company disclosures and network facts, historic destination
  references, the weekly regional FSC mechanism, IATA's full-year 2026 fuel
  forecast, and the public-domain OurAirports airport metadata subset.
- **SYNTHETIC:** shipment IDs/dates/weights/volumes, assignments, individual
  carrier quotes, contract/spot/owned prices, booking capacity, SLA, rejected
  candidates and weekly fuel values. Publicly named partners do not establish
  that any simulated shipment used those carriers.
- **DERIVED:** landed cost, optimizer recommendation and optimized cost, savings,
  savings %, lane/carrier aggregates, monthly trends and rate mix.

The source registry, field formulas, lane classifications and demo manifest live
in `backend/data/provenance/`; versioned public facts and airport metadata live in
`backend/data/sources/`. The dashboard's **Data Sources & Assumptions** action and
KPI information buttons expose these committed records. The heatmap explains lane
classification; shipment audits explain input and output provenance. Twelve AI
provenance questions use deterministic local answers before any optional LLM.

KUL–DEL remains a synthetic demonstration lane, with no confirmed direct Teleport
route claimed. KUL–BOM and other documented KUL destinations reference the 2022
announcement, not a current schedule. All existing lanes remain; six public
historic destinations (SYD, HKG, ICN, HND, TPE, BKI) were added. Partner Air A/B
became Synthetic Partner 01/02, and Myanmar Airways International was added.
Emirates SkyCargo remains for existing comparison flows, explicitly as a synthetic
demo carrier with no sourced Teleport partnership asserted. Owned freighter names
represent three synthetic aircraft with public A321F fleet-type calibration.

The IATA $152/barrel figure is a full-year forecast published in June, not an
observed Jan–Jun mean. Later public network and FSC snapshots provide retrospective
calibration only. The supplied FSC URL resolves to an 8–14 September title despite
its 15–21 September slug; no September rates enter Jan–Jun records. Weekly fuel
values vary synthetically around $152/barrel; `fuel_price_usd` is a synthetic
USD/litre conversion using 158.987 litres/barrel. Candidate surcharge = weight ×
max(weekly index − $90, 0) × synthetic 0.006 coefficient × synthetic regional lane
factor × candidate multiplier, rounded to cents. Base and other costs are also
synthetic; their sum with surcharge gives landed cost. Rate type is not guaranteed
to be cheapest. The unchanged optimizer applies all existing feasibility rules.

Potential saving = SUM(max(actual_paid − optimized_cost, 0)); aggregate saving % =
SUM(potential_saving) / SUM(actual_paid) × 100. Already Optimal includes zero-gap
historical fallback when no candidate is feasible. Average Saving uses positive-gap
shipments only. These formulas always apply to the active filter scope.

Manual snapshot maintenance (never runs on Render startup):

```sh
cd backend
.venv/bin/python scripts/refresh_public_sources.py          # offline validation
.venv/bin/python scripts/refresh_public_sources.py --fetch  # conservative verification/refresh
.venv/bin/python scripts/refresh_public_sources.py --import-dir /path/to/reviewed-snapshots
.venv/bin/python scripts/generate_demo.py
```

A failed download, changed page layout, or unverified fact retains the previous
snapshot and prints `RETAINED`; changed facts require reviewed JSON snapshots.
No key, paid API or database is needed. Airport refresh keeps the existing subset.
Review registry changes before committing. Regenerate and run tests after any
calibration changes. Generation uses fixed seed **20261002**, 2,000 shipments,
Jan–Jun 2026 and deterministic fixture TP-88213 on KUL–BOM. `--output-dir` allows
isolated reproduction; `--generated-at` fixes manifest timestamps for comparisons.
CSV content is reproducible; normal manifest generation records the current UTC
execution timestamp. Company revenue/volume figures are context, never scaled into
synthetic shipment financials or displayed demo savings.

`backend/data/provenance/cost_inputs.csv` records exact simulated market bases,
candidate multipliers, regional factors, coefficients and weekly fuel inputs for
every option. The shipment drawer exposes these inputs in a collapsed audit
section. The manifest includes SHA-256 digests of source snapshots and generated
CSVs, making the precise calibration artifacts and calculation inputs reviewable.
