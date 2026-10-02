# Data credibility upgrade — 2 October 2026

Modified the existing application in place. The optimizer, canonical CSV schemas,
existing routes, navigation, AI dock, suggestion chips, filters, New Chat behavior,
API/CORS configuration and deployment configuration retain their existing behavior.
The provenance endpoint and audit metadata are additive. No deployment was performed.

1. **Public sources incorporated** (committed local snapshots):
   - [Teleport official 1H 2026 results](https://www.teleport.it/newsroom/teleport-1h-financial-results) — OFFICIAL_TELEPORT; publisher Teleport.
   - [Teleport Network](https://www.teleport.it/the-teleport-network) — OFFICIAL_TELEPORT; publisher Teleport.
   - [Teleport historical cargo destinations (2022)](https://www.teleport.it/newsroom/teleport-launches-12-cargo-destinations) — OFFICIAL_TELEPORT; publisher Teleport.
   - [Teleport weekly fuel surcharge mechanism](https://help.teleport.it/article/15-september-2026---21-september-2026-fuel-surcharge-fsc-rates/7226) — OFFICIAL_TELEPORT; publisher Teleport.
   - [IATA 2026 fuel outlook](https://www.iata.org/en/pressroom/2026-releases/06-07-middle-east-disruptions-high-fuel-prices-halve-airline-industry-profitability/) — OFFICIAL_INDUSTRY; publisher IATA.
   - [OurAirports airport metadata](https://ourairports.com/data/) — OPEN_DATA; publisher OurAirports.

2. **Synthetic fields:** shipment identifiers/dates/weights/volumes, origin and
   destination assignments using public airport geography, carrier assignments,
   base/other costs, contract/spot/owned quotes, departure dates, booking capacity,
   availability, SLA and rejected candidate conditions. Fuel values are synthetic
   weekly variations around the public full-year IATA benchmark. The fuel
   coefficient, lane factors and candidate multipliers are synthetic. No commercial
   shipment-level field is presented as a public historical record.
3. **Derived outputs:** landed cost and paid amount (sum of cost components), fuel
   surcharge (weight × index excess × simulated coefficient/factors), feasible
   recommendation and optimized cost, nonnegative potential saving, savings %,
   already-optimal share, average positive saving, lane/carrier/monthly aggregates
   and actual/recommended rate mix. Costs and recommendations come from the existing
   optimizer; KPI values use active filter scope.
4. **Regenerated savings:** **6.6981298538%** (displayed as **6.70%**); synthetic actual
   spend **$13,975,691.58**, optimized spend **$13,039,581.61**, potential saving
   **$936,109.97**. This is derived demo output, not actual Teleport historical savings.
5. **Dataset:** **2,000 shipments**, **13,147 candidate options**, **181 fuel rows**;
   January–June 2026; seed **20261002**. TP-88213 is a deterministic KUL–BOM fixture.
   Isolated repeat generation produces identical CSVs and timestamp-fixed manifests.
6. **Names/geography:** all 12 original lanes retained; KUL–SYD/HKG/ICN/HND/TPE/BKI
   added (18 total). KUL–DEL explicitly remains SYNTHETIC_DEMO_LANE. Public KUL
   classifications reference historic destination geography, not current direct
   schedules. Partner Air A/B became Synthetic Partner 01/02; Myanmar Airways
   International added. MASkargo, Turkish Cargo and three owned freighter names
   remain. Emirates SkyCargo remains for required comparisons, explicitly as a
   synthetic demo carrier without a claimed Teleport partnership. Nine carriers
   represent a subset, not the publicly listed 55+ partners.
7. **Existing AI regression:** all **20 required question flows passed**, including
   lane/carrier comparisons and contextual Why? / Show me those shipments / carrier
   recommendation follow-ups. All pre-existing backend tests also pass.
8. **Provenance AI:** all **12 required questions passed**; answers load registry,
   field provenance and manifest before any optional LLM. Tests ensure the provider
   cannot be called for these answers. Official source URLs are clickable in the AI.
9. **Backend:** **231 tests passed** in the complete suite; the final targeted
   provenance run also passed **20 tests** after CSV newline normalization.
10. **Frontend:** **33 tests passed**, including new sources-drawer, KPI action,
    source-link, heatmap classification, shipment provenance and error-state checks.
11. **Production build:** TypeScript + Vite **passed**. `git diff --check` passed.
    Offline manual source validation passed **6/6**. Simulated download failure
    retains snapshots byte-for-byte. Source and dataset SHA-256 digests verified.
    Browser visual inspection was unavailable because no browser was connected;
    component checks do not establish pixel-level layout fidelity.

The September FSC reference's actual title is 8–14 September despite its URL slug.
Only the mechanism is used; no September rates are copied into Jan–Jun records.
The IATA benchmark is a June full-year forecast, not actual daily observations.
Company disclosures and the October network snapshot supply calibration context,
not proof of shipment activity or Jan–Jun direct route operations. Refresh is a
manual maintenance command; normal startup uses local files and requires no
public websites, API keys, paid services or database. No refresh runs on startup.

12. **Exact files added/changed** (paths relative to the project root):

### Added

- `DATA_CREDIBILITY_REPORT.md`
- `backend/app/services/provenance.py`
- `backend/data/provenance/cost_inputs.csv`
- `backend/data/provenance/demo_manifest.json`
- `backend/data/provenance/field_provenance.json`
- `backend/data/provenance/lane_provenance.json`
- `backend/data/provenance/source_registry.json`
- `backend/data/sources/airports_reference.csv`
- `backend/data/sources/iata_fuel_2026.json`
- `backend/data/sources/teleport_1h_2026.json`
- `backend/data/sources/teleport_fsc_reference.json`
- `backend/data/sources/teleport_network.json`
- `backend/data/sources/teleport_route_references.json`
- `backend/scripts/refresh_public_sources.py`
- `backend/tests/test_provenance.py`
- `frontend/src/components/Provenance.tsx`
- `frontend/src/test/Provenance.test.tsx`

### Changed

- `README.md`
- `backend/app/api/dashboard.py`
- `backend/app/api/shipments.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/analytics_service.py`
- `backend/data/carrier_options.csv`
- `backend/data/fuel_index.csv`
- `backend/data/shipments.csv`
- `backend/scripts/generate_demo.py`
- `frontend/src/App.tsx`
- `frontend/src/components/AIAnalyst.tsx`
- `frontend/src/components/Drawer.tsx`
- `frontend/src/components/LaneHeatmap.tsx`
- `frontend/src/styles.css`
- `frontend/src/types/index.ts`
