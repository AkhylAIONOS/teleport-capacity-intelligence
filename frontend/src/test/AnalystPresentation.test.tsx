import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AIAnalyst } from "../components/AIAnalyst";
import { ProvenanceAnswer } from "../components/Provenance";
import {
  metricLabel,
  normalizeAnalystResponse,
  plainAnalystText,
} from "../services/analystResponse";

describe("AI provenance presentation hotfix", () => {
  it.each([
    ["Actual spen&#x64;", "Actual spend"],
    ["Optimized spen&#100;", "Optimized spend"],
    ["Potential savin&amp;#x67;", "Potential saving"],
    ["Actual spen&amp;amp;#x64;", "Actual spend"],
    ["PUBLIC&nbsp;&amp;&nbsp;SYNTHETIC", "PUBLIC\u00a0&\u00a0SYNTHETIC"],
    ["IATA &mdash; Fuel &copy;", "IATA — Fuel ©"],
  ])("decodes %s as plain text", (encoded, expected) => {
    expect(plainAnalystText(encoded)).toBe(expected);
  });
  it("normalizes all response text and keys without changing filters", () => {
    const input = {
      answer:
        "Actual spen&#x64;. Optimized spen&#100;. Potential savin&amp;#x67;.",
      metrics: {
        "actual_spen&#x64;": 100,
        "optimized_spen&#100;": 80,
        "potential_savin&amp;#x67;": 20,
        label: "Fuel &amp; costs",
      },
      table: [
        {
          "actual_spen&#x64;": 100,
          "optimized_spen&#100;": 80,
          "potential_savin&amp;#x67;": 20,
          carrier: "Synthetic &amp; Partner",
        },
      ],
      chart: {
        type: "trend",
        rows: [{ "actual_spen&#x64;": 100, month: "2026-0&#x36;" }],
      },
      filters: { lane: "KUL-BOM", min_saving: 300 },
    };
    const result = normalizeAnalystResponse(input);
    expect(result.answer).toBe(
      "Actual spend. Optimized spend. Potential saving.",
    );
    expect(result.metrics).toEqual({
      actual_spend: 100,
      optimized_spend: 80,
      potential_saving: 20,
      label: "Fuel & costs",
    });
    expect(result.table[0]).toEqual({
      actual_spend: 100,
      optimized_spend: 80,
      potential_saving: 20,
      carrier: "Synthetic & Partner",
    });
    expect(result.chart?.rows[0]).toEqual({
      actual_spend: 100,
      month: "2026-06",
    });
    expect(result.filters).toEqual(input.filters);
    expect(input.answer).toContain("&#x64;");
    expect(metricLabel("actual_spen&#x64;")).toBe("Actual spend");
    expect(metricLabel("optimized_spen&#100;")).toBe("Optimized spend");
    expect(metricLabel("potential_savin&amp;#x67;")).toBe("Potential saving");
  });
  it("renders decoded markup as harmless text", () => {
    const { container } = render(
      <ProvenanceAnswer text="&lt;img src=x onerror=alert(1)&gt; Actual spen&#x64;" />,
    );
    expect(container.textContent).toContain(
      "<img src=x onerror=alert(1)> Actual spend",
    );
    expect(container.querySelector("img")).toBeNull();
    expect(metricLabel("&lt;script&gt;")).toBe("Metric");
  });
  it("keeps public/synthetic/derived sections separate", () => {
    const { container } = render(
      <ProvenanceAnswer
        text={
          "PUBLIC\nPublic facts\n\nSYNTHETIC\nSimulated records\n\nDERIVED\nCalculated savings"
        }
      />,
    );
    expect(container.querySelectorAll("br").length).toBe(7);
    expect(container.textContent).toContain("PUBLIC");
    expect(container.textContent).toContain("SYNTHETIC");
    expect(container.textContent).toContain("DERIVED");
  });
  it("keeps source URLs clickable in a multiline source list", () => {
    const { container } = render(
      <ProvenanceAnswer
        text={
          "Sources used for this dashboard:\n- Teleport Network — fleet facts. https://www.teleport.it/the-teleport-network\n- OurAirports — airport metadata. https://ourairports.com/data/"
        }
      />,
    );
    expect(
      screen.getAllByRole("link").map((a) => a.getAttribute("href")),
    ).toEqual([
      "https://www.teleport.it/the-teleport-network",
      "https://ourairports.com/data/",
    ]);
    expect(container.querySelectorAll("br").length).toBe(2);
    expect(container.textContent?.startsWith("Sources used")).toBe(true);
  });
  it("renders readable labels in analyst text, cards and table, including retained text", () => {
    const result = normalizeAnalystResponse({
      answer:
        "Actual spen&#x64;. Optimized spen&#100;. Potential savin&amp;#x67;.",
      metrics: {
        "actual_spen&#x64;": 100,
        "optimized_spen&#100;": 80,
        "potential_savin&amp;#x67;": 20,
      },
      table: [
        {
          "actual_spen&#x64;": 100,
          "optimized_spen&#100;": 80,
          "potential_savin&amp;#x67;": 20,
        },
      ],
    });
    const { container } = render(
      <AIAnalyst
        filters={{}}
        isDemo={true}
        onApply={vi.fn()}
        onClose={vi.fn()}
        messages={[
          { role: "analyst", text: result.answer, result },
          { role: "analyst", text: "Retained message: Actual spen&#x64;" },
        ]}
        setMessages={vi.fn()}
        context={{}}
        setContext={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Actual spend. Optimized spend. Potential saving."),
    ).toBeTruthy();
    expect(screen.getByText("Retained message: Actual spend")).toBeTruthy();
    expect(
      Array.from(container.querySelectorAll(".metric-mini small")).map(
        (n) => n.textContent,
      ),
    ).toEqual(["Actual spend", "Optimized spend", "Potential saving"]);
    expect(
      Array.from(container.querySelectorAll(".mini-table th")).map(
        (n) => n.textContent,
      ),
    ).toEqual(["Potential saving", "Actual spend", "Optimized spend"]);
    expect(container.textContent).not.toMatch(/&#x|&#\d|&amp;/);
  });
});
