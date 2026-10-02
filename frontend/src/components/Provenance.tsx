import { useEffect, useState } from "react";
import { Info } from "lucide-react";
import { Panel } from "./Drawer";
import { api } from "../services/api";

type Field = {
  classification: string;
  description?: string;
  formula?: string;
  source_ids: string[];
};
type Source = {
  source_id: string;
  title: string;
  publisher: string;
  url: string;
  source_type: string;
  retrieved_at: string;
  facts_used: Record<string, unknown>;
  notes: string;
};
export type Provenance = {
  source_registry: Source[];
  field_provenance: Record<string, Field>;
  demo_manifest: {
    dataset_name: string;
    random_seed: number;
    generated_at: string;
    note: string;
    shipment_count: number;
    candidate_option_count: number;
    carriers: Record<
      string,
      { classification: string; note: string; fleet_type?: string }
    >;
  };
  lane_provenance: Record<
    string,
    { classification: string; note: string; source_ids: string[] }
  >;
};
export function KPIInfo({
  field,
  onOpen,
}: {
  field: string;
  onOpen: (field: string) => void;
}) {
  return (
    <button
      className="provenance-info icon-button"
      aria-label={`Data provenance for ${field.replaceAll("_", " ")}`}
      onClick={() => onOpen(field)}
      title="Classification, inputs and formula"
    >
      <Info size={13} />
    </button>
  );
}
export function SourcesDrawer({
  field,
  onClose,
}: {
  field: string;
  onClose: () => void;
}) {
  const [data, setData] = useState<Provenance | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const ctrl = new AbortController();
    api<Provenance>("/api/dashboard/provenance", {}, ctrl.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => ctrl.abort();
  }, []);
  const focus = data?.field_provenance[field];
  return (
    <Panel
      title="Data Sources & Assumptions"
      subtitle="Public-source-calibrated synthetic data"
      onClose={onClose}
    >
      <div className="panel-body provenance-body">
        {error && <p role="alert">{error}</p>}
        {!data && !error && <p>Loading source snapshots…</p>}
        {data && (
          <>
            <p>{data.demo_manifest.note}</p>
            {focus && (
              <section className="explanation">
                <h3>{field.replaceAll("_", " ")}</h3>
                <p>
                  CLASSIFICATION:{" "}
                  {field === "shipment_count"
                    ? "SYNTHETIC DATASET COUNT"
                    : focus.classification}
                </p>
                <p>FORMULA: {focus.formula}</p>
                <p>
                  INPUTS: public-source-calibrated synthetic shipment records
                </p>
                <p>{focus.description}</p>
              </section>
            )}
            <section>
              <h3>PUBLIC FACTS</h3>
              {data.source_registry.map((source) => (
                <article key={source.source_id}>
                  <h4>
                    <a href={source.url} target="_blank" rel="noreferrer">
                      {source.title}
                    </a>
                  </h4>
                  <p>
                    {source.publisher} · {source.source_type} · Retrieved{" "}
                    {source.retrieved_at}
                  </p>
                  <dl>
                    {Object.entries(source.facts_used).map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>
                          {Array.isArray(value)
                            ? value.join(", ")
                            : String(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  <p className="muted">{source.notes}</p>
                </article>
              ))}
            </section>
            <section>
              <h3>SYNTHETIC ASSUMPTIONS</h3>
              <p>
                These values are simulated for demonstration and are not
                Teleport historical records.
              </p>
              <p>
                Individual shipment weights, carrier rates, contract/spot
                quotes, available capacity at booking time, SLA conditions and
                historical shipment choices.
              </p>
              <p>
                Daily fuel values and Jan–Jun FSC amounts are synthetic; public
                sources calibrate the benchmark and mechanism.
              </p>
              <p>
                Emirates SkyCargo is retained as a synthetic demonstration
                carrier for comparisons; no Teleport partnership is claimed.
              </p>
              <p>
                Seed {data.demo_manifest.random_seed} ·{" "}
                {data.demo_manifest.shipment_count.toLocaleString()} shipments ·{" "}
                {data.demo_manifest.candidate_option_count.toLocaleString()}{" "}
                options.
              </p>
            </section>
            <section>
              <h3>DERIVED METRICS</h3>
              {Object.entries(data.field_provenance)
                .filter(([, value]) =>
                  value.classification.startsWith("DERIVED"),
                )
                .map(([key, value]) => (
                  <p key={key}>
                    <b>{key.replaceAll("_", " ")}</b>
                    <br />
                    {value.formula}
                    <br />
                    <small>{value.description}</small>
                  </p>
                ))}
            </section>
            <section>
              <h3>LANE PROVENANCE</h3>
              {Object.entries(data.lane_provenance).map(([lane, value]) => (
                <p key={lane}>
                  <b>
                    {lane} · {value.classification}
                  </b>
                  <br />
                  {value.note}
                  <br />
                  <small>Source IDs: {value.source_ids.join(", ")}</small>
                </p>
              ))}
            </section>
          </>
        )}
      </div>
    </Panel>
  );
}

export function ProvenanceAnswer({ text }: { text: string }) {
  return (
    <>
      {text.split(/(https:\/\/[^\s;]+)/g).map((part, index) => {
        if (!part.startsWith("https://")) return part;
        const url = part.replace(/[.,]+$/, "");
        try {
          const host = new URL(url).hostname;
          if (
            ![
              "www.teleport.it",
              "help.teleport.it",
              "www.iata.org",
              "ourairports.com",
            ].includes(host)
          )
            return part;
          return (
            <span key={index}>
              <a href={url} target="_blank" rel="noreferrer">
                {url}
              </a>
              {part.slice(url.length)}
            </span>
          );
        } catch {
          return part;
        }
      })}
    </>
  );
}
