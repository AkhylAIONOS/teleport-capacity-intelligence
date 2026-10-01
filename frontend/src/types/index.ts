export type Filters = {
  shipment_ids?: string[];
  start_date?: string;
  end_date?: string;
  origin?: string;
  destination?: string;
  lane?: string;
  carrier?: string;
  recommended_carrier?: string;
  rate_type?: string;
  recommended_rate_type?: string;
  min_saving?: number;
  search?: string;
};
export type Row = Record<string, string | number | boolean | null>;
export type Scope = {
  start_date: string | null;
  end_date: string | null;
  shipment_count: number;
  data_mode: string;
  currency: string;
};
export type Summary = {
  actual_spend: number;
  optimized_spend: number;
  potential_saving: number;
  saving_percent: number;
  shipment_count: number;
  flagged_shipments: number;
  average_saving_per_flagged: number;
  feasible_shipments: number;
  unchanged_shipments: number;
  already_optimal_percent: number;
  no_feasible_alternative: number;
  data_scope: Scope;
};
export type Metadata = {
  origins: string[];
  destinations: string[];
  lanes: string[];
  carriers: string[];
  rate_types: string[];
  data_scope: Scope;
  quality: Record<string, number>;
};
export type Shipments = {
  rows: Row[];
  total: number;
  page: number;
  page_size: number;
};
export type Detail = {
  shipment: Row;
  recommended_option: Row | null;
  candidates: Row[];
  explanation: string;
};
export type AIResponse = {
  answer: string;
  intent: string;
  metrics: Record<string, unknown>;
  table: Row[];
  filters: Filters;
  chart: { type: string; rows: Row[] } | null;
  confidence: string;
  data_scope: Scope;
  context: Record<string, unknown>;
  provider: string;
};
