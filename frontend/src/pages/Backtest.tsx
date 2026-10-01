import { CheckCircle2, ArrowRight } from "lucide-react";
import type { Summary } from "../types";
import { number, money } from "../services/api";
export function Backtest({ summary: s }: { summary: Summary }) {
  const steps = [
    "Identify recorded historical candidates",
    "Reject unavailable options",
    "Enforce required shipment capacity",
    "Enforce recorded SLA feasibility",
    "Validate total landed cost and components",
    "Select the cheapest feasible option; break ties deterministically",
    "Compare with actual payment; floor savings at zero",
  ];
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Backtest results</h2>
          <p>
            A reproducible audit of historical decisions against available
            capacity.
          </p>
        </div>
        <span className="badge">DETERMINISTIC ENGINE</span>
      </div>
      <div className="backtest-stats">
        {[
          ["Total shipments", s.shipment_count],
          ["Feasible alternatives", s.feasible_shipments],
          ["Shipments improved", s.flagged_shipments],
          ["Shipments unchanged", s.unchanged_shipments],
          ["No feasible alternative", s.no_feasible_alternative],
        ].map(([label, v]) => (
          <div className="card" key={label}>
            <span>{label}</span>
            <strong>{number(v)}</strong>
          </div>
        ))}
      </div>
      <div className="backtest-spend card">
        <div>
          <span>Actual spend</span>
          <strong>{money(s.actual_spend)}</strong>
        </div>
        <ArrowRight />
        <div>
          <span>Optimized spend</span>
          <strong>{money(s.optimized_spend)}</strong>
        </div>
        <div className="saving">
          <span>Potential saving</span>
          <strong>{money(s.potential_saving)}</strong>
        </div>
      </div>
      <section className="card methodology">
        <h3>Optimization methodology</h3>
        <p>
          Independent shipment backtesting, using only recorded candidate
          options.
        </p>
        {steps.map((step, i) => (
          <div key={step}>
            <span>{i + 1}</span>
            <p>{step}</p>
            <CheckCircle2 size={17} />
          </div>
        ))}
        <p className="footnote">
          No feasible option: retain the historical decision and paid cost.
          Capacity is checked per shipment; this MVP does not model competition
          for shared flight capacity. A feasible recommendation can cost more
          than the historical choice; that produces zero potential saving.
        </p>
      </section>
    </>
  );
}
