import { Component, type ReactNode } from "react";
export class AnalystBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: Error) {
    console.error("AI analyst render failed:", error);
  }
  render() {
    return this.state.failed ? (
      <div className="analyst-fallback" role="alert">
        <h3>AI Capacity Analyst</h3>
        <p>AI Analyst could not load. Please retry.</p>
        <button
          className="secondary"
          onClick={() => this.setState({ failed: false })}
        >
          Retry analyst
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
