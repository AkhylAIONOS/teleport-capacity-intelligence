import { useEffect, useState, useRef } from "react";
import { X, ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import type { Detail, Row } from "../types";
import { api, exactMoney, number, percent, dateLabel } from "../services/api";
export function Panel({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const listener = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab") {
        const nodes = Array.from(
          ref.current?.querySelectorAll<HTMLElement>(
            'a[href],button:not(:disabled),input,select,textarea,summary,[tabindex="0"]',
          ) || [],
        );
        if (!nodes.length) return;
        if (e.shiftKey && document.activeElement === nodes[0]) {
          e.preventDefault();
          nodes.at(-1)?.focus();
        } else if (!e.shiftKey && document.activeElement === nodes.at(-1)) {
          e.preventDefault();
          nodes[0].focus();
        }
      }
    };
    document.addEventListener("keydown", listener);
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", listener);
      document.body.style.overflow = old;
      previous?.focus();
    };
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={onClose}>
      <aside
        className="panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        ref={ref}
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <header className="panel-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button
            className="icon-button"
            aria-label="Close panel"
            onClick={onClose}
          >
            <X size={21} />
          </button>
        </header>
        {children}
      </aside>
    </div>
  );
}
export function ShipmentDrawer({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const ctrl = new AbortController();
    api<Detail>("/api/shipments/" + encodeURIComponent(id), {}, ctrl.signal)
      .then(setDetail)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, [id]);
  const d = detail?.shipment;
  const rec = detail?.recommended_option;
  const decision = (recommended: boolean) => {
    if (!d) return null;
    const r: Row = recommended
      ? rec || {
          carrier: d.actual_carrier,
          rate_type: d.actual_rate_type,
          departure_date: d.actual_departure_date,
          base_cost: d.actual_base_cost,
          fuel_surcharge: d.actual_fuel_surcharge,
          other_cost: d.actual_other_cost,
          total_landed_cost: d.actual_paid,
        }
      : {
          carrier: d.actual_carrier,
          rate_type: d.actual_rate_type,
          departure_date: d.actual_departure_date,
          base_cost: d.actual_base_cost,
          fuel_surcharge: d.actual_fuel_surcharge,
          other_cost: d.actual_other_cost,
          total_landed_cost: d.actual_paid,
        };
    return (
      <section className={"decision " + (recommended ? "recommended" : "")}>
        <h4>{recommended ? "RECOMMENDED DECISION" : "ACTUAL DECISION"}</h4>
        <h3>{r.carrier}</h3>
        <p>
          {r.rate_type} · Departure {dateLabel(r.departure_date)}
        </p>
        {[
          ["Base cost", "base_cost"],
          ["Fuel surcharge", "fuel_surcharge"],
          ["Other cost", "other_cost"],
          [recommended ? "Optimized cost" : "Total paid", "total_landed_cost"],
        ].map(([label, key]) => (
          <div className="cost-row" key={key}>
            <span>{label}</span>
            <b>{exactMoney(r[key])}</b>
          </div>
        ))}
      </section>
    );
  };
  return (
    <Panel title={id} subtitle="Historical decision audit" onClose={onClose}>
      <div className="panel-body">
        {error ? (
          <div className="error">{error}</div>
        ) : !detail ? (
          <div className="skeleton tall" />
        ) : (
          <>
            <div className="route-title">
              {d?.origin}
              <ArrowRight size={22} />
              {d?.destination}
            </div>
            <p className="muted">
              {dateLabel(d?.shipment_date)} · {number(d?.weight_kg)} kg ·{" "}
              {d?.volume_cbm} m³
            </p>
            <div className="decision-grid">
              {decision(false)}
              {decision(true)}
            </div>
            <div className="saving-callout">
              <span>Potential saving</span>
              <strong>{exactMoney(d?.potential_saving)}</strong>
              <b>{percent(d?.saving_percent)}</b>
            </div>
            <section className="explanation">
              <h3>
                <ShieldCheck size={18} />
                Why this option?
              </h3>
              <p>{detail.explanation}</p>
              <small>
                {d?.status === "NO_FEASIBLE_ALTERNATIVE"
                  ? "Historical fallback"
                  : `${d?.feasible_count} feasible / ${d?.candidate_count} candidates`}
              </small>
            </section>
            <section className="explanation">
              <h3>Data provenance</h3>
              <p>
                Shipment record and actual carrier assignment: SYNTHETIC.
                Airport metadata: PUBLIC OPEN DATA (OurAirports). Candidate
                options: SYNTHETIC CALIBRATED. Fuel component: DERIVED FROM
                PUBLIC-BENCHMARK-CALIBRATED SYNTHETIC FUEL SERIES.
                Recommendation: DETERMINISTIC OPTIMIZER OUTPUT. These are not
                actual Teleport historical records.
              </p>
            </section>
            {detail.provenance && (
              <section className="explanation">
                {detail.provenance.lane && (
                  <p>
                    {detail.provenance.lane.classification}:{" "}
                    {detail.provenance.lane.note}
                  </p>
                )}
                {!!detail.provenance.cost_inputs.length && (
                  <details>
                    <summary>Exact synthetic cost calculation inputs</summary>
                    <p>
                      Base = market base × candidate multiplier. Other = market
                      other × candidate multiplier. Fuel = weight × max(weekly
                      index − benchmark, 0) × fuel coefficient × lane factor ×
                      candidate multiplier. Round each component to cents, then
                      sum for landed cost.
                    </p>
                    {detail.provenance.cost_inputs.map((row) => (
                      <details key={String(row.option_id)}>
                        <summary>{row.option_id}</summary>
                        <dl>
                          {Object.entries(row)
                            .filter(([key]) => key !== "shipment_id")
                            .map(([key, value]) => (
                              <div key={key}>
                                <dt>{key.replaceAll("_", " ")}</dt>
                                <dd>{String(value)}</dd>
                              </div>
                            ))}
                        </dl>
                      </details>
                    ))}
                  </details>
                )}
              </section>
            )}
            <h3>Historical candidates</h3>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {[
                      "Carrier / rate",
                      "Capacity / required",
                      "Landed cost",
                      "Decision",
                    ].map((x) => (
                      <th key={x}>{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {detail.candidates.map((r) => (
                    <tr key={String(r.option_id)}>
                      <td>
                        {r.carrier}
                        <small className="block muted">
                          {r.rate_type} · {dateLabel(r.departure_date)}
                        </small>
                      </td>
                      <td>
                        {number(r.capacity_available_kg)} /{" "}
                        {number(r.required_capacity_kg)} kg
                      </td>
                      <td>{exactMoney(r.total_landed_cost)}</td>
                      <td>
                        {r.feasible ? (
                          <span className="feasible">
                            <CheckCircle2 size={12} />
                            Feasible
                          </span>
                        ) : (
                          <span className="rejected">{r.reason}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="footnote">
              Recorded alternatives only. Each shipment is optimized
              independently; shared flight capacity is not allocated across
              shipments.
            </p>
          </>
        )}
      </div>
    </Panel>
  );
}
