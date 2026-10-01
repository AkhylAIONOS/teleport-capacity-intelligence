import { vi, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);
Element.prototype.scrollIntoView = vi.fn();
Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
  value: () => ({
    width: 800,
    height: 300,
    top: 0,
    left: 0,
    bottom: 300,
    right: 800,
    x: 0,
    y: 0,
    toJSON() {},
  }),
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
