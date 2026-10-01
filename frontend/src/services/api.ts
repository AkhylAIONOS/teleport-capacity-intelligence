import type { Filters } from "../types";
const base =
  (import.meta as unknown as { env: Record<string, string> }).env
    .VITE_API_BASE_URL || "";
export async function api<T>(
  path: string,
  filters: Filters | Record<string, unknown> = {},
  signal?: AbortSignal,
): Promise<T> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "")
      params.set(k, Array.isArray(v) ? JSON.stringify(v) : String(v));
  });
  const res = await fetch(base + path + (params.size ? "?" + params : ""), {
    signal,
  });
  if (!res.ok)
    throw new Error(
      `Request failed (${res.status}). Check the backend and filter values.`,
    );
  return res.json();
}
export async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(base + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok)
    throw new Error(
      `Analyst request failed (${res.status}). Please try again.`,
    );
  return res.json();
}
export const money = (value: unknown) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
export const exactMoney = (value: unknown) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    Number(value) || 0,
  );
export const number = (value: unknown) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(
    Number(value) || 0,
  );
export const percent = (value: unknown) => `${Number(value || 0).toFixed(1)}%`;

export function monthLabel(value: unknown, withYear = false): string {
  const text = String(value ?? "");
  if (!/^\d{4}-(0[1-9]|1[0-2])/.test(text)) return text;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    ...(withYear ? { year: "numeric" as const } : {}),
    timeZone: "UTC",
  }).format(new Date(text.slice(0, 7) + "-01T00:00:00Z"));
}
export function dateLabel(value: unknown): string {
  const text = String(value ?? "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return text || "—";
  const dt = new Date(text + "T00:00:00Z");
  return Number.isNaN(dt.getTime())
    ? text
    : new Intl.DateTimeFormat("en-US", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      }).format(dt);
}
export function monthRange(month: string): {
  start_date: string;
  end_date: string;
} {
  const [year, num] = month.split("-").map(Number);
  const last = new Date(Date.UTC(year, num, 0)).getUTCDate();
  return {
    start_date: month + "-01",
    end_date: month + "-" + String(last).padStart(2, "0"),
  };
}
