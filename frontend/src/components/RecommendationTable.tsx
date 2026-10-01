import { ArrowUpRight, ArrowRight } from "lucide-react";
import type { Shipments } from "../types";
import { exactMoney, dateLabel, number } from "../services/api";
export function RecommendationTable({
  data,
  onOpen,
  onViewAll,
}: {
  data: Shipments;
  onOpen: (id: string) => void;
  onViewAll: () => void;
}) {
  return (
    <section className="card recommendation-card">
      <div className="card-heading">
        <div>
          <h3>Shipment recommendations</h3>
          <p>Lowest feasible historical options · largest savings first</p>
        </div>
        <button className="secondary" onClick={onViewAll}>
          View all shipments <ArrowRight size={13} />
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {[
                "Shipment",
                "Recommended carrier",
                "Day",
                "Rate type",
                "Optimized cost",
                "Actual paid",
                "Δ Savings",
              ].map((label) => (
                <th key={label}>{label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.slice(0, 6).map((r) => (
              <tr
                key={String(r.shipment_id)}
                onClick={() => onOpen(String(r.shipment_id))}
              >
                <td>
                  <button
                    className="shipment-link"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(String(r.shipment_id));
                    }}
                  >
                    {r.shipment_id}
                    <ArrowUpRight size={12} />
                  </button>
                </td>
                <td>
                  <span className={r.changed_carrier ? "changed" : ""}>
                    {r.recommended_carrier}
                  </span>
                </td>
                <td title={dateLabel(r.recommended_departure_date)}>
                  {r.recommended_departure_date
                    ? new Intl.DateTimeFormat("en-US", {
                        weekday: "short",
                        timeZone: "UTC",
                      }).format(
                        new Date(
                          String(r.recommended_departure_date) + "T00:00:00Z",
                        ),
                      )
                    : "—"}
                </td>
                <td>
                  <span className={r.changed_rate_type ? "changed" : ""}>
                    {r.recommended_rate_type}
                  </span>
                </td>
                <td>{exactMoney(r.optimized_cost)}</td>
                <td>{exactMoney(r.actual_paid)}</td>
                <td className="saving">
                  {Number(r.potential_saving) > 0 ? "+" : ""}
                  {exactMoney(r.potential_saving)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.rows.length && (
          <div className="empty">No shipments match these filters.</div>
        )}
      </div>
      <div className="recommendation-footer">
        Showing {number(Math.min(data.rows.length, 6))} of {number(data.total)}{" "}
        scored shipments. Recorded alternatives only.
      </div>
    </section>
  );
}
