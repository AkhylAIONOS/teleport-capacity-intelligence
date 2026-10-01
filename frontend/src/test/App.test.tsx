import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import type { Row } from "../types";

// Fixtures model transport only; analytics correctness is tested against the CSVs in Python.
const shipment: Row = {
  shipment_id: "TP-88213",
  shipment_date: "2026-06-10",
  origin: "KUL",
  destination: "DEL",
  lane: "KUL-DEL",
  weight_kg: 100,
  volume_cbm: 1,
  actual_carrier: "MASkargo",
  actual_rate_type: "Contract",
  actual_departure_date: "2026-06-11",
  actual_base_cost: 850,
  actual_fuel_surcharge: 100,
  actual_other_cost: 50,
  actual_paid: 1000,
  recommended_carrier: "Partner Air A",
  recommended_rate_type: "Spot",
  recommended_departure_date: "2026-06-11",
  optimized_cost: 800,
  potential_saving: 200,
  saving_percent: 20,
  changed_carrier: true,
  changed_rate_type: true,
  feasible_count: 1,
  candidate_count: 2,
  status: "OPTIMIZED",
};
const scope = {
  start_date: "2026-01-01",
  end_date: "2026-06-30",
  shipment_count: 2000,
  data_mode: "demo",
  currency: "USD",
};
const summary = {
  actual_spend: 100000,
  optimized_spend: 80000,
  potential_saving: 20000,
  saving_percent: 20,
  shipment_count: 2000,
  flagged_shipments: 1000,
  average_saving_per_flagged: 20,
  feasible_shipments: 1990,
  unchanged_shipments: 1000,
  already_optimal_percent: 50,
  no_feasible_alternative: 10,
  data_scope: scope,
};
let calls: string[] = [];
beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      calls.push(String(input));
      const url = new URL(String(input), "http://localhost");
      let body: unknown;
      if (url.pathname.endsWith("/metadata"))
        body = {
          origins: ["KUL"],
          destinations: ["DEL", "BOM"],
          lanes: ["KUL-DEL", "KUL-BOM"],
          carriers: ["MASkargo", "Partner Air A"],
          rate_types: ["Contract", "Spot", "Owned"],
          data_scope: scope,
          quality: { shipment_rows_loaded: 2000, missing_costs: 0 },
        };
      else if (url.pathname.endsWith("/summary"))
        body = url.searchParams.get("lane")
          ? {
              ...summary,
              actual_spend: 1000,
              optimized_spend: 800,
              potential_saving: 200,
              shipment_count: 1,
            }
          : summary;
      else if (url.pathname === "/api/shipments/TP-88213")
        body = {
          shipment,
          recommended_option: {
            option_id: "O1",
            carrier: "Partner Air A",
            rate_type: "Spot",
            departure_date: "2026-06-11",
            base_cost: 650,
            fuel_surcharge: 100,
            other_cost: 50,
            total_landed_cost: 800,
          },
          candidates: [
            {
              option_id: "O1",
              carrier: "Partner Air A",
              rate_type: "Spot",
              capacity_available_kg: 120,
              required_capacity_kg: 100,
              total_landed_cost: 800,
              feasible: true,
              reason: "Feasible",
            },
            {
              option_id: "O2",
              carrier: "MASkargo",
              rate_type: "Contract",
              capacity_available_kg: 50,
              required_capacity_kg: 100,
              total_landed_cost: 700,
              feasible: false,
              reason: "Insufficient capacity",
            },
          ],
          explanation:
            "Partner Air A was recommended because it is the lowest feasible cost.",
        };
      else if (url.pathname === "/api/shipments")
        body = { rows: [shipment], total: 1, page: 1, page_size: 15 };
      else if (url.pathname.endsWith("/lanes"))
        body = [
          {
            lane: "KUL-DEL",
            actual_spend: 1000,
            optimized_spend: 800,
            potential_saving: 200,
            saving_percent: 20,
            shipment_count: 1,
          },
        ];
      else if (url.pathname.endsWith("/lane-heatmap"))
        body = [
          {
            lane: "KUL-DEL",
            month: "2026-06",
            actual_spend: 1000,
            optimized_spend: 800,
            potential_saving: 200,
            saving_percent: 20,
            shipment_count: 1,
            intensity: 1,
          },
        ];
      else if (url.pathname.endsWith("/carriers")) body = [];
      else if (url.pathname.endsWith("/rate-mix")) body = [];
      else if (url.pathname.endsWith("/trends")) body = [];
      else if (url.pathname.endsWith("/chat")) {
        const request = JSON.parse(String(init?.body));
        body = {
          answer: "Dashboard filters applied. DEMO / simulated data.",
          intent: "FILTER_COMMAND",
          metrics: { potential_saving: 200 },
          table: [],
          filters: { lane: "KUL-DEL" },
          chart: null,
          confidence: "high",
          data_scope: scope,
          context: { last_lane: "KUL-DEL" },
          provider: "mock",
        };
        expect(request.message).toContain("KUL");
      }
      return { ok: true, status: 200, json: async () => body } as Response;
    }),
  );
});
describe("Dashboard interactions", () => {
  it("loads backend metrics and refetches all charts/table when a lane filter changes", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("$100,000");
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-DEL");
    await waitFor(() => expect(screen.queryByText("$100,000")).toBeNull());
    for (const path of [
      "summary",
      "trends",
      "lanes",
      "carriers",
      "rate-mix",
      "lane-heatmap",
    ])
      expect(
        calls.some(
          (c) => c.includes("/" + path + "?") && c.includes("lane=KUL-DEL"),
        ),
      ).toBe(true);
    expect(
      calls.some(
        (c) => c.includes("/api/shipments?") && c.includes("lane=KUL-DEL"),
      ),
    ).toBe(true);
  });
  it("opens a shipment drawer showing actual/recommended costs and rejected candidate reasons", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole("button", { name: "TP-88213" }));
    await screen.findByText("Historical candidates");
    expect(screen.getByText("Insufficient capacity")).toBeTruthy();
    expect(screen.getByText("ACTUAL DECISION")).toBeTruthy();
    expect(screen.getByText("RECOMMENDED DECISION")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Close panel" }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });
  it("applies AI filter commands automatically and shows grounded response", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("$100,000");
    await user.click(screen.getByLabelText("Ask an analytics question"));
    await user.type(
      screen.getByLabelText("Ask an analytics question"),
      "Show KUL to DEL shipments.",
    );
    await user.click(screen.getByRole("button", { name: "Send question" }));
    await screen.findByText(
      "Dashboard filters applied. DEMO / simulated data.",
    );
    await waitFor(() =>
      expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe(
        "KUL-DEL",
      ),
    );
    expect(
      screen.getByRole("heading", { name: "Teleport Capacity Intelligence" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Ask an analytics question")).toBeTruthy();
    expect(screen.getByText("Dashboard updated to KUL → DEL.")).toBeTruthy();
  });
  it("reset clears filters and restores overall metrics", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("$100,000");
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-DEL");
    await waitFor(() => expect(screen.queryByText("$100,000")).toBeNull());
    await user.click(screen.getByRole("button", { name: "Reset" }));
    await screen.findByText("$100,000");
    expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe("");
  });
  it("renders an actionable error when backend requests fail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 503 })),
    );
    render(<App />);
    await screen.findByRole("button", { name: "Retry" });
    expect(
      screen.getByText(/Check the backend and filter values/),
    ).toBeTruthy();
  });
});

function mockChat(
  reply: unknown | ((request: Record<string, any>) => unknown),
  fail = false,
) {
  const original = globalThis.fetch;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string, init?: RequestInit) => {
      if (String(input).startsWith("/api/ai/chat")) {
        if (fail) return { ok: false, status: 503 } as Response;
        const body =
          typeof reply === "function"
            ? reply(JSON.parse(String(init?.body)))
            : reply;
        return { ok: true, status: 200, json: async () => body } as Response;
      }
      return original(input, init);
    }),
  );
}
async function sendQuestion(
  user: ReturnType<typeof userEvent.setup>,
  question: string,
) {
  await user.type(screen.getByLabelText("Ask an analytics question"), question);
  await user.click(screen.getByRole("button", { name: "Send question" }));
}
describe("Brief layout and inline analyst regressions", () => {
  it("keeps four compact KPIs, recommendation table, and exactly three visuals on Overview", async () => {
    const { container } = render(<App />);
    await screen.findByText("Shipment recommendations");
    expect(container.querySelectorAll(".compact-kpis .kpi")).toHaveLength(4);
    expect(
      container.querySelectorAll(".overview-analytics > section"),
    ).toHaveLength(3);
    expect(
      container
        .querySelector(".recommendation-card")!
        .compareDocumentPosition(
          container.querySelector(".overview-analytics")!,
        ) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Ask AI Analyst" })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByLabelText("Ask an analytics question")).toBeTruthy();
    expect(calls.some((c) => c.includes("cumulative=true"))).toBe(true);
  });
  it("heatmap cell selects lane and month, refetches every visual, and updates analyst context", async () => {
    const user = userEvent.setup();
    let request: Record<string, any> | null = null;
    mockChat((req: Record<string, any>) => {
      request = req;
      return { answer: "Scope verified.", metrics: {}, table: [], filters: {} };
    });
    render(<App />);
    const cell = await screen.findByRole("button", {
      name: /KUL-DEL Jun 2026 savings/,
    });
    await user.hover(cell);
    expect(screen.getByRole("tooltip").textContent).toContain(
      "Potential saving",
    );
    await user.click(cell);
    await waitFor(() =>
      expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe(
        "KUL-DEL",
      ),
    );
    expect(
      (screen.getByLabelText("Start date") as HTMLInputElement).value,
    ).toBe("2026-06-01");
    expect((screen.getByLabelText("End date") as HTMLInputElement).value).toBe(
      "2026-06-30",
    );
    await waitFor(() =>
      expect(
        calls.some(
          (c) =>
            c.includes("/api/dashboard/lane-heatmap?") &&
            c.includes("lane=KUL-DEL") &&
            c.includes("start_date=2026-06-01"),
        ),
      ).toBe(true),
    );
    await sendQuestion(user, "Why?");
    await screen.findByText("Scope verified.");
    expect(request!.context.last_lane).toBe("KUL-DEL");
    expect(request!.context.last_date_range.start_date).toBe("2026-06-01");
  });
  it("lane label filters without imposing a new month and Reset restores scope", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("$100,000");
    await user.click(
      screen.getByRole("button", { name: "Filter lane KUL-DEL" }),
    );
    await waitFor(() => expect(screen.queryByText("$100,000")).toBeNull());
    expect(
      (screen.getByLabelText("Start date") as HTMLInputElement).value,
    ).toBe("");
    await user.click(screen.getByRole("button", { name: "Reset" }));
    await screen.findByText("$100,000");
    expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe("");
  });
  it("savings question uses the current dashboard scope and renders the backend answer", async () => {
    const user = userEvent.setup();
    let sent: Record<string, any> | null = null;
    mockChat((req: Record<string, any>) => {
      sent = req;
      return {
        answer: "Computed savings in your selected scope.",
        metrics: { potential_saving: shipment.potential_saving },
        data_scope: { ...scope, shipment_count: 1 },
        filters: {},
      };
    });
    render(<App />);
    await screen.findByText("$100,000");
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-DEL");
    await waitFor(() => expect(screen.queryByText("$100,000")).toBeNull());
    await sendQuestion(user, "How much could we have saved?");
    await screen.findByText("Computed savings in your selected scope.");
    expect(sent!.filters.lane).toBe("KUL-DEL");
    expect(
      screen
        .getByText("Computed savings in your selected scope.")
        .closest(".message")!.textContent,
    ).toContain("$200");
  });
  it("retains lane follow-up context and applies filters without closing chat or leaving Overview", async () => {
    const user = userEvent.setup();
    const requests: Record<string, any>[] = [];
    mockChat((req: Record<string, any>) => {
      requests.push(req);
      if (req.message === "Why?")
        return {
          answer: "Recorded alternatives explain the cost gap.",
          intent: "LANE_ANALYSIS",
          context: { last_lane: "KUL-DEL" },
          filters: {},
        };
      if (req.message.startsWith("Show me"))
        return {
          answer: "Filtered shipment scope.",
          intent: "FILTER_COMMAND",
          context: { last_lane: "KUL-DEL" },
          filters: { lane: "KUL-DEL" },
        };
      return {
        answer: "KUL-DEL has the highest computed opportunity.",
        intent: "TOP_LANES",
        context: { last_lane: "KUL-DEL" },
        filters: {},
      };
    });
    render(<App />);
    await screen.findByText("$100,000");
    await sendQuestion(user, "Which lane has the highest savings opportunity?");
    await screen.findByText("KUL-DEL has the highest computed opportunity.");
    await sendQuestion(user, "Why?");
    await screen.findByText("Recorded alternatives explain the cost gap.");
    expect(requests[1].context.last_lane).toBe("KUL-DEL");
    await sendQuestion(user, "Show me those shipments.");
    await screen.findByText("Dashboard updated to KUL → DEL.");
    await waitFor(() =>
      expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe(
        "KUL-DEL",
      ),
    );
    expect(
      screen.getByRole("heading", { name: "Teleport Capacity Intelligence" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Ask an analytics question")).toBeTruthy();
  });
  it("applies June and saving-threshold AI actions to all analytics", async () => {
    const user = userEvent.setup();
    mockChat({
      answer: "June shipments above the threshold.",
      intent: "FILTER_COMMAND",
      filters: {
        start_date: "2026-06-01",
        end_date: "2026-06-30",
        min_saving: 300,
      },
    });
    render(<App />);
    await screen.findByText("$100,000");
    await sendQuestion(user, "Show June shipments above $300 saving.");
    await screen.findByText("June shipments above the threshold.");
    await waitFor(() =>
      expect(
        (screen.getByLabelText("Minimum saving") as HTMLInputElement).value,
      ).toBe("300"),
    );
    for (const name of ["summary", "trends", "lane-heatmap", "rate-mix"])
      await waitFor(() =>
        expect(
          calls.some(
            (c) =>
              c.includes("/" + name + "?") &&
              c.includes("min_saving=300") &&
              c.includes("start_date=2026-06-01"),
          ),
        ).toBe(true),
      );
  });
  it("keeps conversation on collapse/reopen and on filter changes", async () => {
    const user = userEvent.setup();
    mockChat({
      answer: "Saved conversation.",
      context: { last_lane: "KUL-DEL" },
      filters: {},
    });
    render(<App />);
    await screen.findByText("$100,000");
    await sendQuestion(user, "How much could we have saved?");
    await screen.findByText("Saved conversation.");
    const controls = screen.getAllByRole("button", {
      name: "Collapse AI analyst",
    });
    await user.click(controls[0]);
    expect(screen.queryByRole("button", { name: "Send question" })).toBeNull();
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-DEL");
    await user.click(screen.getByRole("button", { name: "Open AI analyst" }));
    expect(screen.getByText("Saved conversation.")).toBeTruthy();
    expect(screen.getByLabelText("Ask an analytics question")).toBeTruthy();
  });
  it.each([null, {}, [], { answer: "" }])(
    "handles empty/malformed response %j without blanking the dashboard",
    async (reply) => {
      const user = userEvent.setup();
      mockChat(reply);
      render(<App />);
      await screen.findByText("$100,000");
      await sendQuestion(user, "Savings?");
      await screen.findByText("AI Analyst could not load. Please retry.");
      expect(screen.getByText("Shipment recommendations")).toBeTruthy();
      expect(
        screen.getByRole("button", { name: "Retry analyst" }),
      ).toBeTruthy();
    },
  );
  it("renders partial responses safely when metrics, filters, chart, scope or table are malformed", async () => {
    const user = userEvent.setup();
    mockChat({
      answer: "Partial response handled.",
      metrics: null,
      table: [null, 7, {}],
      filters: null,
      data_scope: null,
      chart: { rows: null },
    });
    render(<App />);
    await screen.findByText("$100,000");
    await sendQuestion(user, "Savings?");
    await screen.findByText("Partial response handled.");
    expect(screen.getByText("Shipment recommendations")).toBeTruthy();
    expect(
      screen.queryByText("AI Analyst could not load. Please retry."),
    ).toBeNull();
  });
  it("shows in-chat retry on API failure while the dashboard continues working", async () => {
    const user = userEvent.setup();
    mockChat({}, true);
    render(<App />);
    await screen.findByText("$100,000");
    await sendQuestion(user, "Savings?");
    await screen.findByText("AI Analyst could not load. Please retry.");
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-DEL");
    await waitFor(() => expect(screen.queryByText("$100,000")).toBeNull());
    expect(screen.getByText("Shipment recommendations")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Retry analyst" })).toBeTruthy();
  });
  it("formats months as labels while retaining ISO filter values", async () => {
    render(<App />);
    await screen.findByText("Shipment recommendations");
    expect(screen.getByRole("columnheader", { name: "Jun" })).toBeTruthy();
    expect(screen.queryByRole("columnheader", { name: "2026-06" })).toBeNull();
  });
  it("View all shipments preserves the full table and navigation pages", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("Shipment recommendations");
    await user.click(
      screen.getByRole("button", { name: "View all shipments" }),
    );
    await screen.findByText("Historical shipments");
    expect(
      screen.getByRole("columnheader", { name: /Actual carrier/ }),
    ).toBeTruthy();
    for (const name of ["Lanes", "Carriers", "Backtest", "Data Quality"])
      expect(screen.getByRole("button", { name })).toBeTruthy();
  });
});

it("automatically applies structured filters from any supported analyst result", async () => {
  const user = userEvent.setup();
  mockChat({
    answer: "Relevant shipment subset.",
    intent: "TOP_SHIPMENTS",
    filters: { lane: "KUL-DEL", min_saving: 300 },
  });
  render(<App />);
  await screen.findByText("$100,000");
  await sendQuestion(user, "Show top 10 missed-saving shipments");
  await screen.findByText("Dashboard updated to KUL → DEL.");
  expect(
    (screen.getByLabelText("Minimum saving") as HTMLInputElement).value,
  ).toBe("300");
  expect(
    screen.getByRole("heading", { name: "Teleport Capacity Intelligence" }),
  ).toBeTruthy();
});

describe("Final chat polish", () => {
  it("keeps one persistent suggestion area and sends chips through chat", async () => {
    const user = userEvent.setup();
    const requests: Record<string, any>[] = [];
    mockChat((req: Record<string, any>) => {
      requests.push(req);
      return { answer: `Computed answer ${requests.length}.`, filters: {} };
    });
    render(<App />);
    await screen.findByText("Shipment recommendations");
    await user.click(
      screen.getByRole("button", { name: "How much could we have saved?" }),
    );
    await screen.findByText("Computed answer 1.");
    expect(
      screen.getByLabelText("Try asking").querySelectorAll("button"),
    ).toHaveLength(5);
    expect(
      screen.getAllByRole("button", { name: "How much could we have saved?" }),
    ).toHaveLength(1);
    await user.click(
      screen.getByRole("button", { name: "Give me a monthly summary" }),
    );
    await screen.findByText("Computed answer 2.");
    expect(requests[1].message).toBe("Give me a monthly summary");
  });
  it("New Chat clears every context reference and preserves dashboard scope and open dock", async () => {
    const user = userEvent.setup();
    const requests: Record<string, any>[] = [];
    mockChat((req: Record<string, any>) => {
      requests.push(req);
      return {
        answer: "Previous answer.",
        filters: {},
        context: {
          last_lane: "KUL-BOM",
          last_carrier: "MASkargo",
          last_shipment: "TP-88213",
          last_lanes: ["KUL-BOM", "KUL-DEL"],
          last_result_ids: ["TP-88213"],
          last_date_range: { start_date: "2026-06-01" },
          last_intent: "SHIPMENT_LOOKUP",
        },
      };
    });
    render(<App />);
    await screen.findByText("Shipment recommendations");
    await user.selectOptions(screen.getByLabelText("Lane"), "KUL-BOM");
    await sendQuestion(user, "Analyze shipment TP-88213.");
    await screen.findByText("Previous answer.");
    await user.click(screen.getByRole("button", { name: "Start new chat" }));
    expect(screen.queryByText("Previous answer.")).toBeNull();
    expect(screen.getByText("Your backtest, explained.")).toBeTruthy();
    expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe(
      "KUL-BOM",
    );
    await sendQuestion(user, "How much could we have saved?");
    await screen.findByText("Previous answer.");
    expect(requests[1].context).toEqual({});
    expect(requests[1].filters.lane).toBe("KUL-BOM");
  });
  it("ignores a pending response after New Chat, including its filters and context", async () => {
    const user = userEvent.setup();
    const original = globalThis.fetch;
    let complete!: (value: Response) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) =>
        String(input).startsWith("/api/ai/chat")
          ? new Promise<Response>((resolve) => {
              complete = resolve;
            })
          : original(input, init),
      ),
    );
    render(<App />);
    await screen.findByText("Shipment recommendations");
    await sendQuestion(user, "Why?");
    await user.click(screen.getByRole("button", { name: "Start new chat" }));
    complete({
      ok: true,
      json: async () => ({
        answer: "Stale response.",
        intent: "FILTER_COMMAND",
        filters: { lane: "KUL-DEL" },
        context: { last_lane: "KUL-DEL" },
      }),
    } as Response);
    await waitFor(() =>
      expect(
        screen.queryByText("Calculating from historical rows…"),
      ).toBeNull(),
    );
    expect(screen.queryByText("Stale response.")).toBeNull();
    expect((screen.getByLabelText("Lane") as HTMLSelectElement).value).toBe("");
    expect(screen.getByText("Your backtest, explained.")).toBeTruthy();
  });
  it("renders canonical and encoded metric identifiers as safe readable labels", async () => {
    const user = userEvent.setup();
    mockChat({
      answer: "Safe metric labels.",
      metrics: {
        "actual_spen&#x64;": 1,
        "optimized_spen&#100;": 2,
        "potential_savin&amp;#x67;": 3,
        "saving_chang&#x65;": 4,
      },
      filters: {},
    });
    const { container } = render(<App />);
    await screen.findByText("Shipment recommendations");
    await sendQuestion(user, "Give me metrics");
    await screen.findByText("Safe metric labels.");
    const labels = Array.from(
      container.querySelectorAll(".metric-mini small"),
    ).map((e) => e.textContent);
    expect(labels).toEqual([
      "Actual spend",
      "Optimized spend",
      "Potential saving",
      "Saving change",
    ]);
    expect(labels.join(" ")).not.toMatch(/&#x|&#|&amp;/);
  });
});
