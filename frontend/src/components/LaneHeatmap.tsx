import { useState } from "react";
import type { Row, Filters } from "../types";
import { money, percent, monthLabel, monthRange } from "../services/api";
export function LaneHeatmap({
  rows,
  onApply,
}: {
  rows: Row[];
  onApply: (f: Filters) => void;
}) {
  const [hover, setHover] = useState<Row | null>(null);
  const lanes = [...new Set(rows.map((r) => String(r.lane)))].sort();
  const months = [...new Set(rows.map((r) => String(r.month)))].sort();
  const cells = new Map(rows.map((r) => [`${r.lane}:${r.month}`, r]));
  const laneNote = (row: Row) => {
    const p = row.provenance as
      { classification?: string; note?: string } | undefined;
    return p ? `${p.classification}: ${p.note}` : "Lane provenance unavailable";
  };
  const multiYear = new Set(months.map((m) => m.slice(0, 4))).size > 1;
  return (
    <section className="card heatmap-card">
      <div className="card-heading">
        <div>
          <h3>Savings gap by lane</h3>
          <p>Lane × month · select to explore</p>
        </div>
      </div>
      <div className="heatmap-scroll">
        <table className="lane-heatmap">
          <thead>
            <tr>
              <th>Lane</th>
              {months.map((m) => (
                <th key={m}>{monthLabel(m, multiYear)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lanes.map((lane) => (
              <tr key={lane}>
                <th>
                  <button
                    aria-label={`Filter lane ${lane}`}
                    onClick={() => onApply({ lane })}
                  >
                    {lane.replace("-", " → ")}
                  </button>
                </th>
                {months.map((month) => {
                  const row = cells.get(`${lane}:${month}`);
                  return (
                    <td key={month}>
                      {row ? (
                        <button
                          className="heat-cell"
                          aria-label={`${lane} ${monthLabel(month, true)} savings ${money(row.potential_saving)}`}
                          style={{
                            background: `rgba(0,127,121,${0.07 + 0.83 * Number(row.intensity || 0)})`,
                          }}
                          onMouseEnter={() => setHover(row)}
                          onMouseLeave={() => setHover(null)}
                          onFocus={() => setHover(row)}
                          onBlur={() => setHover(null)}
                          onClick={() =>
                            onApply({ lane, ...monthRange(month) })
                          }
                          title={`${laneNote(row)}\n${lane} · ${monthLabel(month, true)}\nActual spend: ${money(row.actual_spend)}\nOptimized spend: ${money(row.optimized_spend)}\nPotential saving: ${money(row.potential_saving)}\nSaving: ${percent(row.saving_percent)}`}
                        >
                          <span className="sr-only">
                            {money(row.potential_saving)}
                          </span>
                        </button>
                      ) : (
                        <span
                          className="heat-cell missing"
                          title="No shipments in this period"
                        >
                          —
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <div className="empty">No lane periods match this scope.</div>
      )}
      <div className="heatmap-caption">
        <span>Lower</span>
        <div />
        <span>Higher savings</span>
      </div>
      {hover && (
        <div className="heatmap-tooltip" role="tooltip">
          <b>
            {String(hover.lane).replace("-", " → ")} ·{" "}
            {monthLabel(hover.month, true)}
          </b>
          <span>
            Actual spend <strong>{money(hover.actual_spend)}</strong>
          </span>
          <span>
            Optimized spend <strong>{money(hover.optimized_spend)}</strong>
          </span>
          <span>
            Potential saving <strong>{money(hover.potential_saving)}</strong>
          </span>
          <small>{laneNote(hover)}</small>
          <span>
            Saving rate <strong>{percent(hover.saving_percent)}</strong>
          </span>
        </div>
      )}
    </section>
  );
}
