import type { AIResponse, Filters, Row, Scope } from "../types";
export type AnalystResult = Omit<AIResponse, "data_scope"> & {
  data_scope: Scope | null;
};
const object = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);
const primitive = (v: unknown) =>
  v === null ||
  typeof v === "string" ||
  typeof v === "boolean" ||
  (typeof v === "number" && Number.isFinite(v));
export function safeFilters(value: unknown): Filters {
  if (!object(value)) return {};
  const out: Record<string, unknown> = {};
  for (const key of [
    "lane",
    "origin",
    "destination",
    "carrier",
    "recommended_carrier",
    "search",
  ])
    if (typeof value[key] === "string" && value[key].length <= 200)
      out[key] = value[key];
  for (const key of ["start_date", "end_date"])
    if (
      value[key] === null ||
      (typeof value[key] === "string" &&
        /^\d{4}-\d{2}-\d{2}$/.test(value[key] as string))
    )
      out[key] = value[key];
  for (const key of ["rate_type", "recommended_rate_type"])
    if (
      value[key] === null ||
      ["Contract", "Spot", "Owned"].includes(String(value[key]))
    )
      out[key] = value[key];
  if (
    typeof value.min_saving === "number" &&
    Number.isFinite(value.min_saving) &&
    value.min_saving >= 0
  )
    out.min_saving = value.min_saving;
  if (
    Array.isArray(value.shipment_ids) &&
    value.shipment_ids.length <= 100 &&
    value.shipment_ids.every((v) => typeof v === "string")
  )
    out.shipment_ids = value.shipment_ids;
  return out as Filters;
}
export function normalizeAnalystResponse(value: unknown): AnalystResult {
  if (
    !object(value) ||
    typeof value.answer !== "string" ||
    !value.answer.trim()
  )
    throw new Error("Empty or invalid analyst response");
  const table = Array.isArray(value.table)
    ? value.table
        .filter(object)
        .map(
          (r) =>
            Object.fromEntries(
              Object.entries(r).filter(([, v]) => primitive(v)),
            ) as Row,
        )
    : [];
  const metrics = object(value.metrics)
    ? Object.fromEntries(
        Object.entries(value.metrics)
          .filter(([, v]) => primitive(v))
          .map(([k, v]) => [canonicalMetricKey(k), v]),
      )
    : {};
  const scope = value.data_scope;
  const data_scope =
    object(scope) &&
    typeof scope.shipment_count === "number" &&
    Number.isFinite(scope.shipment_count) &&
    scope.shipment_count >= 0 &&
    ["string", "object"].includes(typeof scope.start_date) &&
    ["string", "object"].includes(typeof scope.end_date) &&
    (scope.start_date === null || typeof scope.start_date === "string") &&
    (scope.end_date === null || typeof scope.end_date === "string")
      ? (scope as Scope)
      : null;
  const chart =
    object(value.chart) &&
    value.chart.type === "trend" &&
    Array.isArray(value.chart.rows)
      ? {
          type: "trend",
          rows: value.chart.rows
            .filter(object)
            .map(
              (r) =>
                Object.fromEntries(
                  Object.entries(r).filter(([, v]) => primitive(v)),
                ) as Row,
            ),
        }
      : null;
  return {
    answer: value.answer,
    intent:
      typeof value.intent === "string" &&
      !(value.intent === "FILTER_COMMAND" && !object(value.filters))
        ? value.intent
        : "UNSUPPORTED",
    metrics,
    table,
    filters: safeFilters(value.filters),
    chart,
    confidence:
      typeof value.confidence === "string" ? value.confidence : "unsupported",
    data_scope,
    context: object(value.context) ? value.context : {},
    provider: typeof value.provider === "string" ? value.provider : "mock",
  };
}

// Only canonical identifiers become labels; response strings never become HTML.
export function metricLabel(key: string): string {
  if (!/^[a-z][a-z0-9_]*$/.test(key)) return "Metric";
  const label = key.replaceAll("_", " ");
  return label[0].toUpperCase() + label.slice(1);
}

function canonicalMetricKey(key: string): string {
  // Decode numeric ASCII identifier characters only, never markup or arbitrary HTML.
  return key
    .replace(/&amp;(?=#)/g, "&")
    .replace(/&#(?:x([0-9a-f]+)|(\d+));/gi, (entity, hex, decimal) => {
      const code = parseInt(hex || decimal, hex ? 16 : 10);
      if (code > 127) return entity;
      const character = String.fromCharCode(
        parseInt(hex || decimal, hex ? 16 : 10),
      );
      return /^[a-z0-9_]$/i.test(character) ? character : entity;
    });
}
