import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  SourcesDrawer,
  KPIInfo,
  ProvenanceAnswer,
} from "../components/Provenance";
import { LaneHeatmap } from "../components/LaneHeatmap";
import { ShipmentDrawer } from "../components/Drawer";

const provenance = {
  source_registry: [
    {
      source_id: "network",
      title: "Teleport Network",
      publisher: "Teleport",
      url: "https://www.teleport.it/the-teleport-network",
      source_type: "OFFICIAL_TELEPORT",
      retrieved_at: "2026-10-02",
      facts_used: { owned_freighters: 3, air_partners_min: 55 },
      notes: "Network calibration only",
    },
  ],
  field_provenance: {
    potential_saving: {
      classification: "DERIVED",
      formula: "SUM(max(actual_paid - optimized_cost, 0))",
      description: "Not actual Teleport historical savings.",
      source_ids: [],
    },
  },
  demo_manifest: {
    note: "Synthetic records, not actual Teleport historical results.",
    random_seed: 20261002,
    shipment_count: 2000,
    candidate_option_count: 13147,
  },
  lane_provenance: {
    "KUL-DEL": {
      classification: "SYNTHETIC_DEMO_LANE",
      note: "Used for demonstration; not claimed as an actual historical Teleport lane.",
      source_ids: ["ourairports"],
    },
  },
};
beforeEach(() =>
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => provenance })),
  ),
);
describe("data provenance", () => {
  it("makes official provenance URLs clickable without interpreting HTML", () => {
    render(
      <ProvenanceAnswer text="Source: https://www.teleport.it/the-teleport-network. <script>bad</script>" />,
    );
    expect(screen.getByRole("link").getAttribute("href")).toBe(
      "https://www.teleport.it/the-teleport-network",
    );
    expect(document.querySelector("script")).toBeNull();
  });
  it("shows public links, assumptions, formulas and lane caveat; closes on Escape", async () => {
    const close = vi.fn();
    render(<SourcesDrawer field="potential_saving" onClose={close} />);
    expect(await screen.findByText("PUBLIC FACTS")).toBeTruthy();
    expect(screen.getByText("SYNTHETIC ASSUMPTIONS")).toBeTruthy();
    expect(screen.getByText("DERIVED METRICS")).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Teleport Network" })
        .getAttribute("href"),
    ).toBe(provenance.source_registry[0].url);
    expect(
      screen.getByText("FORMULA: SUM(max(actual_paid - optimized_cost, 0))"),
    ).toBeTruthy();
    expect(screen.getByText(/KUL-DEL · SYNTHETIC_DEMO_LANE/)).toBeTruthy();
    await userEvent.keyboard("{Escape}");
    expect(close).toHaveBeenCalled();
  });
  it("opens specific KPI provenance with an accessible action", async () => {
    const open = vi.fn();
    render(<KPIInfo field="potential_saving" onOpen={open} />);
    await userEvent.click(
      screen.getByRole("button", {
        name: "Data provenance for potential saving",
      }),
    );
    expect(open).toHaveBeenCalledWith("potential_saving");
  });
  it("shows an actionable fetch failure without inventing sources", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw Error("Offline");
      }),
    );
    render(<SourcesDrawer field="" onClose={() => {}} />);
    expect((await screen.findByRole("alert")).textContent).toContain("Offline");
    expect(screen.queryByText("PUBLIC FACTS")).toBeNull();
  });
  it("shows synthetic lane classification in the heatmap tooltip", async () => {
    const row = {
      lane: "KUL-DEL",
      month: "2026-06",
      potential_saving: 100,
      intensity: 0.5,
      provenance: provenance.lane_provenance["KUL-DEL"],
    };
    render(<LaneHeatmap rows={[row as never]} onApply={() => {}} />);
    await userEvent.hover(
      screen.getByRole("button", { name: /KUL-DEL Jun 2026 savings/ }),
    );
    expect(screen.getByRole("tooltip").textContent).toContain(
      "SYNTHETIC_DEMO_LANE",
    );
    expect(screen.getByRole("tooltip").textContent).toContain(
      "not claimed as an actual historical Teleport lane",
    );
  });
  it("adds shipment provenance without replacing optimizer audit", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
          shipment: {
            origin: "KUL",
            destination: "BOM",
            actual_carrier: "MASkargo",
            actual_paid: 100,
            optimized_cost: 90,
            potential_saving: 10,
          },
          recommended_option: null,
          candidates: [],
          explanation: "Lowest feasible candidate",
        }),
      })),
    );
    render(<ShipmentDrawer id="TP-88213" onClose={() => {}} />);
    expect(await screen.findByText("Data provenance")).toBeTruthy();
    expect(
      screen.getByText(
        /Shipment record and actual carrier assignment: SYNTHETIC/,
      ),
    ).toBeTruthy();
    expect(screen.getByText("Lowest feasible candidate")).toBeTruthy();
  });
});
