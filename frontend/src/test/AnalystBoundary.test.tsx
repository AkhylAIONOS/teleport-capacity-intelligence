import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalystBoundary } from "../components/AnalystBoundary";
import { monthLabel, dateLabel, monthRange } from "../services/api";

describe("Analyst isolation and date presentation", () => {
  it("contains a render exception, keeps the surrounding dashboard visible, and retries", async () => {
    const user = userEvent.setup();
    let broken = true;
    function Content() {
      if (broken)
        throw new TypeError("Cannot convert undefined or null to object");
      return <p>Analyst recovered.</p>;
    }
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <>
        <h1>Dashboard is still visible</h1>
        <AnalystBoundary>
          <Content />
        </AnalystBoundary>
      </>,
    );
    expect(
      screen.getByText("AI Analyst could not load. Please retry."),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Dashboard is still visible" }),
    ).toBeTruthy();
    expect(spy).toHaveBeenCalled();
    broken = false;
    await user.click(screen.getByRole("button", { name: "Retry analyst" }));
    expect(screen.getByText("Analyst recovered.")).toBeTruthy();
  });
  it("formats month/date labels without timezone shifts and uses actual month ends", () => {
    expect(monthLabel("2026-01")).toBe("Jan");
    expect(monthLabel("2026-06", true)).toBe("Jun 2026");
    expect(dateLabel("2026-06-30")).toBe("Jun 30, 2026");
    expect(monthRange("2024-02")).toEqual({
      start_date: "2024-02-01",
      end_date: "2024-02-29",
    });
  });
});
