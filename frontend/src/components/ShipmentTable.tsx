import {
  ArrowDownUp,
  ChevronLeft,
  ChevronRight,
  ArrowUpRight,
} from "lucide-react";
import type { Row, Shipments } from "../types";
import { money, percent, number, dateLabel } from "../services/api";
export function ShipmentTable({
  data,
  page,
  onPage,
  onOpen,
  sort,
  descending,
  onSort,
}: {
  data: Shipments;
  page: number;
  onPage: (n: number) => void;
  onOpen: (id: string) => void;
  sort: string;
  descending: boolean;
  onSort: (key: string) => void;
}) {
  const columns = [
    ["shipment_id", "Shipment"],
    ["shipment_date", "Date"],
    ["lane", "Lane"],
    ["actual_carrier", "Actual carrier"],
    ["recommended_carrier", "Recommended"],
    ["actual_rate_type", "Actual rate"],
    ["recommended_rate_type", "Rec. rate"],
    ["actual_paid", "Actual cost"],
    ["optimized_cost", "Optimized"],
    ["potential_saving", "Saving"],
    ["saving_percent", "Saving %"],
  ];
  const cell = (r: Row, key: string) =>
    key === "potential_saving" ||
    key === "optimized_cost" ||
    key === "actual_paid"
      ? money(r[key])
      : key === "saving_percent"
        ? percent(r[key])
        : key === "shipment_date"
          ? dateLabel(r[key])
          : String(r[key] ?? "—");
  return (
    <>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map(([key, label]) => (
                <th key={key}>
                  <button onClick={() => onSort(key)}>
                    {label}
                    {sort === key ? (
                      <span>{descending ? " ↓" : " ↑"}</span>
                    ) : (
                      <ArrowDownUp size={10} />
                    )}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr
                key={String(r.shipment_id)}
                onClick={() => onOpen(String(r.shipment_id))}
              >
                {columns.map(([key]) => (
                  <td
                    key={key}
                    className={key === "potential_saving" ? "saving" : ""}
                  >
                    {key === "shipment_id" ? (
                      <button
                        className="shipment-link"
                        onClick={(e) => {
                          e.stopPropagation();
                          onOpen(String(r.shipment_id));
                        }}
                      >
                        {r[key]}
                        <ArrowUpRight size={12} />
                      </button>
                    ) : key === "recommended_carrier" && r.changed_carrier ? (
                      <span className="changed">{cell(r, key)}</span>
                    ) : key === "recommended_rate_type" &&
                      r.changed_rate_type ? (
                      <span className="changed">{cell(r, key)}</span>
                    ) : (
                      cell(r, key)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {!data.rows.length && (
          <div className="empty">
            No shipments match your filters. Try widening the date range or
            lowering the saving threshold.
          </div>
        )}
      </div>
      <div className="pagination">
        <span>
          {number(data.total)} shipments · Page {page} of{" "}
          {Math.max(1, Math.ceil(data.total / data.page_size))}
        </span>
        <div>
          <button
            aria-label="Previous page"
            disabled={page <= 1}
            onClick={() => onPage(page - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            aria-label="Next page"
            disabled={page * data.page_size >= data.total}
            onClick={() => onPage(page + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </>
  );
}
