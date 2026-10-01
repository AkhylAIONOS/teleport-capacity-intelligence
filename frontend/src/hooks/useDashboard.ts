import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { Filters, Summary, Row, Shipments } from "../types";
export function useDashboard(
  filters: Filters,
  page: number,
  sort: string,
  descending: boolean,
  cumulative: boolean,
  pageSize = 15,
) {
  const [data, setData] = useState<{
    summary: Summary;
    trends: Row[];
    lanes: Row[];
    heatmap: Row[];
    carriers: Row[];
    rates: Row[];
    shipments: Shipments;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([
      api<Summary>("/api/dashboard/summary", filters, ctrl.signal),
      api<Row[]>(
        "/api/dashboard/trends",
        { ...filters, cumulative },
        ctrl.signal,
      ),
      api<Row[]>("/api/dashboard/lanes", filters, ctrl.signal),
      api<Row[]>("/api/dashboard/carriers", filters, ctrl.signal),
      api<Row[]>("/api/dashboard/lane-heatmap", filters, ctrl.signal),
      api<Row[]>("/api/dashboard/rate-mix", filters, ctrl.signal),
      api<Shipments>(
        "/api/shipments",
        { ...filters, page, page_size: pageSize, sort_by: sort, descending },
        ctrl.signal,
      ),
    ])
      .then(([summary, trends, lanes, carriers, heatmap, rates, shipments]) => {
        setData({
          summary,
          trends,
          lanes,
          carriers,
          heatmap,
          rates,
          shipments,
        });
        setLoading(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => ctrl.abort();
  }, [
    JSON.stringify(filters),
    page,
    sort,
    descending,
    cumulative,
    reload,
    pageSize,
  ]);
  return { data, loading, error, retry: () => setReload((v) => v + 1) };
}
