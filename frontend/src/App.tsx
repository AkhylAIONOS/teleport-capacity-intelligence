import { useState, useEffect, useCallback } from "react";
import {
  Plane,
  LayoutDashboard,
  Package,
  Route,
  Building2,
  FlaskConical,
  ShieldCheck,
  MessageSquare,
  RotateCcw,
  Search,
  ArrowUpRight,
  ArrowRight,
  ChevronDown,
  Menu,
  Download,
  AlertCircle,
} from "lucide-react";
import { api, money, percent, number, dateLabel } from "./services/api";
import type { Filters, Metadata } from "./types";
import { useDashboard } from "./hooks/useDashboard";
import { TrendChart, CarrierChart, RateMix } from "./components/Charts";
import { ShipmentTable } from "./components/ShipmentTable";
import { ShipmentDrawer } from "./components/Drawer";
import { AIAnalyst, type Message } from "./components/AIAnalyst";
import { RecommendationTable } from "./components/RecommendationTable";
import { LaneHeatmap } from "./components/LaneHeatmap";
import { AnalystBoundary } from "./components/AnalystBoundary";
import { Backtest } from "./pages/Backtest";
import { SourcesDrawer, KPIInfo } from "./components/Provenance";
const nav = [
  ["Overview", LayoutDashboard],
  ["Shipments", Package],
  ["Lanes", Route],
  ["Carriers", Building2],
  ["Backtest", FlaskConical],
  ["Data Quality", ShieldCheck],
] as const;
export default function App() {
  const [provenance, setProvenance] = useState<string | null>(null);
  const closeProvenance = useCallback(() => setProvenance(null), []);
  const [view, setView] = useState("Overview");
  const [filters, setFilters] = useState<Filters>({});
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [metaError, setMetaError] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("potential_saving");
  const [descending, setDescending] = useState(true);
  const [cumulative, setCumulative] = useState(true);
  const [drawer, setDrawer] = useState<string | null>(null);
  const [ai, setAI] = useState(true);
  const [mobile, setMobile] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [context, setContext] = useState<Record<string, unknown>>({});
  const [search, setSearch] = useState("");
  const { data, loading, error, retry } = useDashboard(
    filters,
    page,
    sort,
    descending,
    cumulative,
    view === "Overview" ? 6 : 15,
  );
  useEffect(() => {
    api<Metadata>("/api/dashboard/metadata")
      .then(setMeta)
      .catch((e) => setMetaError(e.message));
  }, []);
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((f) => ({ ...f, search: search || undefined }));
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);
  const syncContext = (next: Filters) => {
    setContext((previous) => {
      const updated = { ...previous };
      delete updated.last_result_ids;
      if (next.lane) updated.last_lane = next.lane;
      else {
        delete updated.last_lane;
        delete updated.last_lanes;
      }
      if (next.carrier || next.recommended_carrier)
        updated.last_carrier = next.carrier || next.recommended_carrier;
      else delete updated.last_carrier;
      if (next.start_date || next.end_date)
        updated.last_date_range = {
          start_date: next.start_date || null,
          end_date: next.end_date || null,
        };
      else delete updated.last_date_range;
      delete updated.last_shipment;
      return updated;
    });
  };
  const update = (key: keyof Filters, value: string | number) => {
    const next = { ...filters, [key]: value || undefined };
    setFilters(next);
    syncContext(next);
    setPage(1);
  };
  const apply = (f: Filters) => {
    const next = Object.fromEntries(
      Object.entries(f).filter(
        ([, v]) => v !== null && v !== undefined && v !== "",
      ),
    ) as Filters;
    setFilters(next);
    setSearch(next.search || "");
    setPage(1);
  };
  const applyHeatmap = (patch: Filters) => {
    const next = {
      ...filters,
      ...patch,
      origin: undefined,
      destination: undefined,
      shipment_ids: undefined,
    };
    setFilters(next);
    setPage(1);
    syncContext(next);
  };
  const closeDrawer = useCallback(() => setDrawer(null), []);
  const closeAI = useCallback(() => setAI(false), []);
  const reset = () => {
    setFilters({});
    syncContext({});
    setSearch("");
    setPage(1);
  };
  const s = data?.summary;
  const active = Object.entries(filters).filter(
    ([, v]) => v !== undefined && v !== "" && v !== 0,
  );
  function download() {
    if (!data) return;
    const rows = data.shipments.rows;
    if (!rows.length) return;
    const keys = Object.keys(rows[0]);
    const escape = (v: unknown) =>
      '"' + String(v ?? "").replaceAll('"', '""') + '"';
    const csv = [
      keys.map(escape).join(","),
      ...rows.map((r) => keys.map((k) => escape(r[k])).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "teleport-demo-current-page.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  const filterSelect = (
    label: string,
    key: keyof Filters,
    options: string[],
  ) => (
    <label className="filter" key={key}>
      <span>{label}</span>
      <div>
        <select
          aria-label={label}
          value={String(filters[key] || "")}
          onChange={(e) => update(key, e.target.value)}
        >
          <option value="">
            All {label.toLowerCase()}
            {label === "Rate type" ? "s" : ""}
          </option>
          {options.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
        <ChevronDown size={12} />
      </div>
    </label>
  );
  return (
    <div className={"app-shell " + (ai ? "dock-open" : "dock-closed")}>
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("Overview");
          }}
        >
          <div className="brand-icon">
            <Plane size={24} />
          </div>
          <span>
            teleport<span className="brand-sub">CAPACITY INTELLIGENCE</span>
          </span>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={view === label ? "active" : ""}
              onClick={() => {
                setView(label);
                setMobile(false);
              }}
            >
              <Icon size={18} />
              {label}
              {view === label && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="engine-status">
            <span className="status-dot" />
            <b>Backtest engine</b>
            <small>Deterministic · CSV adapter</small>
          </div>
          <div className="profile">
            <span>TC</span>
            <div>
              <b>Teleport workspace</b>
              <small>Simulated data environment</small>
            </div>
          </div>
        </div>
      </aside>
      {provenance !== null && (
        <SourcesDrawer field={provenance} onClose={closeProvenance} />
      )}
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            Capacity intelligence <span>/</span>
            <b>{view}</b>
          </div>
          <div className="top-actions">
            <button
              className="sources-action"
              onClick={() => setProvenance("")}
            >
              Data Sources &amp; Assumptions
            </button>
            <span className="demo-badge">
              {meta?.data_scope.data_mode === "demo" || !meta
                ? "DEMO DATA"
                : "IMPORTED DATA"}
            </span>
            <button
              className="icon-button analyst-toggle"
              aria-label={ai ? "Collapse AI analyst" : "Open AI analyst"}
              aria-expanded={ai}
              onClick={() => setAI(!ai)}
            >
              <MessageSquare size={18} />
            </button>
          </div>
        </header>
        <div className="workspace">
          <div className="page-heading">
            <div>
              <h1>
                {view === "Overview" ? "Teleport Capacity Intelligence" : view}
              </h1>
              <p>
                {view === "Overview"
                  ? "Historical Capacity & Cost Backtest"
                  : "Explore the recorded decisions behind your capacity performance."}
              </p>
            </div>
            <div className="data-period">
              <span className="status-dot" />
              {dateLabel(
                s?.data_scope.start_date || meta?.data_scope.start_date,
              )}{" "}
              <ArrowRight size={12} />{" "}
              {dateLabel(s?.data_scope.end_date || meta?.data_scope.end_date)}
              <small>Current scope · USD</small>
            </div>
          </div>
          <section className="filter-bar">
            <label className="filter date-filter">
              <span>Date range</span>
              <div>
                <input
                  aria-label="Start date"
                  type="date"
                  value={filters.start_date || ""}
                  onChange={(e) => update("start_date", e.target.value)}
                />
                <span>—</span>
                <input
                  aria-label="End date"
                  type="date"
                  value={filters.end_date || ""}
                  onChange={(e) => update("end_date", e.target.value)}
                />
              </div>
            </label>
            {filterSelect("Origin", "origin", meta?.origins || [])}
            {filterSelect(
              "Destination",
              "destination",
              meta?.destinations || [],
            )}
            {filterSelect("Lane", "lane", meta?.lanes || [])}
            {filterSelect("Carrier", "carrier", meta?.carriers || [])}
            {filterSelect("Rate type", "rate_type", meta?.rate_types || [])}
            <label className="filter minimum">
              <span>Min. saving</span>
              <div>
                <span>$</span>
                <input
                  aria-label="Minimum saving"
                  type="number"
                  min="0"
                  value={filters.min_saving || ""}
                  placeholder="Any"
                  onChange={(e) => update("min_saving", Number(e.target.value))}
                />
              </div>
            </label>
            <button className="reset" onClick={reset} title="Reset filters">
              <RotateCcw size={14} />
              Reset
            </button>
          </section>
          {active.length > 0 && (
            <div className="active-filters">
              {active.map(([k, v]) => (
                <button
                  key={k}
                  onClick={() => {
                    update(k as keyof Filters, "");
                    if (k === "search") setSearch("");
                  }}
                >
                  {k.replaceAll("_", " ")}: {v} ×
                </button>
              ))}
            </div>
          )}
          {error || metaError ? (
            <div className="error">
              <AlertCircle size={18} />
              {error || metaError}
              <button
                onClick={() => {
                  setMetaError("");
                  api<Metadata>("/api/dashboard/metadata")
                    .then(setMeta)
                    .catch((e) => setMetaError(e.message));
                  retry();
                }}
              >
                Retry
              </button>
            </div>
          ) : loading ? (
            <div className="loading-grid" aria-label="Loading dashboard">
              {Array.from({ length: view === "Overview" ? 4 : 6 }, (_, i) => (
                <div key={i} className="skeleton" />
              ))}
              <div className="skeleton tall" />
              <div className="skeleton tall" />
            </div>
          ) : (
            data &&
            s && (
              <>
                {view !== "Data Quality" &&
                  view !== "Backtest" &&
                  (view === "Overview" ? (
                    <>
                      <div className="kpi-grid compact-kpis">
                        <div className="card kpi featured">
                          <strong>{money(s.potential_saving)}</strong>
                          <div className="kpi-label">
                            POTENTIAL SAVINGS IDENTIFIED{" "}
                            <KPIInfo
                              field="potential_saving"
                              onOpen={setProvenance}
                            />
                          </div>
                          <small>
                            {number(s.flagged_shipments)} shipments with
                            opportunity
                          </small>
                        </div>
                        <div className="card kpi">
                          <strong>{number(s.shipment_count)}</strong>
                          <div className="kpi-label">
                            SHIPMENTS SCORED{" "}
                            <KPIInfo
                              field="shipment_count"
                              onOpen={setProvenance}
                            />
                          </div>
                          <small>Validated synthetic shipments</small>
                        </div>
                        <div className="card kpi">
                          <strong>{percent(s.already_optimal_percent)}</strong>
                          <div className="kpi-label">
                            ALREADY OPTIMAL{" "}
                            <KPIInfo
                              field="already_optimal_percent"
                              onOpen={setProvenance}
                            />
                          </div>
                          <small>No positive savings gap</small>
                        </div>
                        <div className="card kpi">
                          <strong>{money(s.average_saving_per_flagged)}</strong>
                          <div className="kpi-label">
                            AVG. SAVING PER FLAGGED SHIPMENT{" "}
                            <KPIInfo
                              field="average_saving_per_flagged"
                              onOpen={setProvenance}
                            />
                          </div>
                          <small>Positive savings only</small>
                        </div>
                      </div>
                      <div className="secondary-spend">
                        <span>
                          Actual spend <b>{money(s.actual_spend)}</b>
                        </span>
                        <span>
                          Optimized spend <b>{money(s.optimized_spend)}</b>
                        </span>
                        <span>
                          Savings opportunity <b>{percent(s.saving_percent)}</b>
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="kpi-grid">
                      {[
                        [
                          "Actual spend",
                          money(s.actual_spend),
                          "Recorded historical payments",
                        ],
                        [
                          "Optimized spend",
                          money(s.optimized_spend),
                          "Lowest feasible candidate costs",
                        ],
                        [
                          "Potential savings",
                          money(s.potential_saving),
                          `${number(s.flagged_shipments)} shipments with opportunity`,
                        ],
                        [
                          "Savings rate",
                          percent(s.saving_percent),
                          "Potential saving / actual spend",
                        ],
                        [
                          "Shipments analysed",
                          number(s.shipment_count),
                          "Validated synthetic shipments",
                        ],
                        [
                          "Avg. flagged saving",
                          money(s.average_saving_per_flagged),
                          "Per shipment with positive saving",
                        ],
                      ].map(([label, value, caption], i) => (
                        <div
                          className={"card kpi " + (i === 2 ? "featured" : "")}
                          key={label}
                        >
                          <div className="kpi-label">
                            {label}
                            {i === 2 && <ArrowUpRight size={16} />}
                          </div>
                          <strong>{value}</strong>
                          <small>{caption}</small>
                        </div>
                      ))}
                    </div>
                  ))}
                {s.shipment_count === 0 && view !== "Data Quality" && (
                  <div className="empty card">
                    No validated shipments match this scope. Reset filters to
                    explore the available dataset.
                  </div>
                )}
                {view === "Overview" && (
                  <>
                    <RecommendationTable
                      data={data.shipments}
                      onOpen={setDrawer}
                      onViewAll={() => {
                        setView("Shipments");
                        setPage(1);
                      }}
                    />
                    <div className="overview-analytics">
                      <section className="card trend-card">
                        <div className="card-heading">
                          <div>
                            <h3>Cumulative savings / Engine vs actual</h3>
                            <p>Recorded cost against lowest feasible cost</p>
                          </div>
                          <div className="segmented">
                            <button
                              className={!cumulative ? "selected" : ""}
                              onClick={() => setCumulative(false)}
                            >
                              Monthly
                            </button>
                            <button
                              className={cumulative ? "selected" : ""}
                              onClick={() => setCumulative(true)}
                            >
                              Cumulative
                            </button>
                          </div>
                        </div>
                        <div className="chart-legend">
                          <span>
                            <i className="navy" />
                            Actual cost
                          </span>
                          <span>
                            <i />
                            Engine cost
                          </span>
                        </div>
                        <TrendChart rows={data.trends} />
                        <p className="trend-caption">
                          Potential savings in this scope:{" "}
                          <b>{money(s.potential_saving)}</b>
                        </p>
                      </section>
                      <LaneHeatmap rows={data.heatmap} onApply={applyHeatmap} />
                      <section className="card overview-rate">
                        <div className="card-heading">
                          <div>
                            <h3>Contracted vs spot mix</h3>
                            <p>Actual mix → recommended mix</p>
                          </div>
                        </div>
                        <RateMix rows={data.rates} />
                      </section>
                    </div>
                  </>
                )}
                {view === "Shipments" && (
                  <section className="card shipment-card">
                    <div className="card-heading">
                      <div>
                        <h3>
                          Historical shipments{" "}
                          <span className="count-badge">
                            {number(data.shipments.total)}
                          </span>
                        </h3>
                        <p>
                          Compare actual decisions with the lowest feasible
                          alternatives.
                        </p>
                      </div>
                      <div className="table-actions">
                        <label className="search">
                          <Search size={14} />
                          <input
                            aria-label="Search shipments"
                            placeholder="Search shipment, lane or carrier"
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                          />
                        </label>
                        <button
                          className="secondary"
                          onClick={() => {
                            setSort("potential_saving");
                            setDescending(true);
                            setPage(1);
                          }}
                        >
                          Highest saving
                        </button>
                        <button
                          className="icon-button"
                          title="Export current page as CSV"
                          aria-label="Export current page"
                          onClick={download}
                        >
                          <Download size={16} />
                        </button>
                      </div>
                    </div>
                    <ShipmentTable
                      data={data.shipments}
                      page={page}
                      onPage={setPage}
                      onOpen={setDrawer}
                      sort={sort}
                      descending={descending}
                      onSort={(key) => {
                        if (sort === key) setDescending(!descending);
                        else {
                          setSort(key);
                          setDescending(true);
                        }
                        setPage(1);
                      }}
                    />
                  </section>
                )}
                {view === "Lanes" && (
                  <section className="card">
                    <div className="card-heading">
                      <div>
                        <h3>Lane opportunity ranking</h3>
                        <p>
                          Ranked by calculated potential savings. Select a lane
                          to filter.
                        </p>
                      </div>
                    </div>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            {[
                              "Lane",
                              "Actual spend",
                              "Optimized spend",
                              "Potential savings",
                              "Savings %",
                              "Shipments",
                            ].map((x) => (
                              <th key={x}>{x}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.lanes.map((r) => (
                            <tr key={String(r.lane)}>
                              <td>
                                <button
                                  className="shipment-link"
                                  onClick={() => {
                                    update("lane", String(r.lane));
                                    setView("Shipments");
                                  }}
                                >
                                  {r.lane}
                                  <ArrowUpRight size={12} />
                                </button>
                              </td>
                              <td>{money(r.actual_spend)}</td>
                              <td>{money(r.optimized_spend)}</td>
                              <td className="saving">
                                {money(r.potential_saving)}
                              </td>
                              <td>{percent(r.saving_percent)}</td>
                              <td>{number(r.shipment_count)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
                {view === "Carriers" && (
                  <section className="card">
                    <div className="card-heading">
                      <div>
                        <h3>Historical carrier performance</h3>
                        <p>
                          Cost gaps reflect the shipment mix assigned to each
                          historical carrier.
                        </p>
                      </div>
                    </div>
                    <CarrierChart rows={data.carriers} />
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            {[
                              "Carrier",
                              "Historical usage",
                              "Actual spend",
                              "Average cost",
                              "Recommended usage",
                              "Potential saving",
                            ].map((x) => (
                              <th key={x}>{x}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.carriers.map((r) => (
                            <tr key={String(r.carrier)}>
                              <td>
                                <button
                                  className="shipment-link"
                                  onClick={() => {
                                    update("carrier", String(r.carrier));
                                    setView("Shipments");
                                  }}
                                >
                                  {r.carrier}
                                  <ArrowUpRight size={12} />
                                </button>
                              </td>
                              <td>{number(r.shipment_count)}</td>
                              <td>{money(r.actual_spend)}</td>
                              <td>{money(r.average_cost)}</td>
                              <td>{number(r.recommended_usage)}</td>
                              <td className="saving">
                                {money(r.potential_saving)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}
                {view === "Backtest" && <Backtest summary={s} />}{" "}
                {view === "Data Quality" && (
                  <>
                    <section className="card quality-header">
                      <ShieldCheck size={28} />
                      <div>
                        <h3>Dataset validation</h3>
                        <p>
                          Raw input checks before optimization. Invalid shipment
                          rows are quarantined; invalid options are rejected.
                          This audit describes the entire loaded dataset and is
                          independent of dashboard filters.
                        </p>
                      </div>
                    </section>
                    <div className="quality-grid">
                      {Object.entries(meta?.quality || {}).map(([k, v]) => (
                        <div className="card" key={k}>
                          <span>{k.replaceAll("_", " ")}</span>
                          <strong
                            className={
                              v > 0 && !/loaded|usable/.test(k) ? "warning" : ""
                            }
                          >
                            {number(v)}
                          </strong>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )
          )}
          <footer className="workspace-footer">
            <span>
              <ShieldCheck size={13} />
              {meta?.data_scope.data_mode === "demo" || !meta
                ? "Simulated demo data. Not real Teleport rates or results."
                : "Imported dataset. Verify source quality before using results."}
            </span>
            <span>Independent shipment backtest · USD</span>
          </footer>
        </div>
      </main>
      {drawer && <ShipmentDrawer id={drawer} onClose={closeDrawer} />}{" "}
      <aside className="analyst-dock" aria-label="Analyst dock" hidden={!ai}>
        <AnalystBoundary>
          <AIAnalyst
            isDemo={meta?.data_scope.data_mode !== "real"}
            filters={filters}
            onApply={apply}
            onClose={closeAI}
            messages={messages}
            setMessages={setMessages}
            context={context}
            setContext={setContext}
          />
        </AnalystBoundary>
      </aside>
    </div>
  );
}
