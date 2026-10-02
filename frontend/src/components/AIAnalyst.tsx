import { ProvenanceAnswer } from "./Provenance";
import { useState, useRef, useEffect } from "react";
import {
  Sparkles,
  ArrowUp,
  SlidersHorizontal,
  PanelRightClose,
  RotateCcw,
} from "lucide-react";
import { TrendChart } from "./Charts";
import {
  post,
  money,
  percent,
  number,
  dateLabel,
  monthLabel,
} from "../services/api";
import {
  metricLabel,
  normalizeAnalystResponse,
  type AnalystResult,
} from "../services/analystResponse";
import type { Filters, Row } from "../types";
const suggestions = [
  "How much could we have saved?",
  "Which lane has the biggest opportunity?",
  "Compare spot vs contract",
  "Show top 10 missed-saving shipments",
  "Give me a monthly summary",
];
export type Message = {
  role: "user" | "analyst" | "action";
  text: string;
  result?: AnalystResult;
  retryQuestion?: string;
};
export function AIAnalyst({
  filters,
  isDemo,
  onApply,
  onClose,
  messages,
  setMessages,
  context,
  setContext,
}: {
  filters: Filters;
  isDemo: boolean;
  onApply: (f: Filters) => void;
  onClose: () => void;
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  context: Record<string, unknown>;
  setContext: (c: Record<string, unknown>) => void;
}) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const session = useRef(0);
  function newChat() {
    session.current += 1;
    setMessages([]);
    setContext({});
    setInput("");
    setBusy(false);
  }
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, busy]);
  function applyAction(f: Filters) {
    onApply(f);
    const subject = f.lane
      ? f.lane.replace("-", " → ")
      : f.origin
        ? `origin ${f.origin}`
        : f.recommended_carrier
          ? `${f.recommended_carrier} recommendations`
          : "the selected scope";
    setMessages((m) => [
      ...m,
      { role: "action", text: `Dashboard updated to ${subject}.` },
    ]);
  }
  async function ask(text: string) {
    if (!text.trim() || busy) return;
    const requestSession = session.current;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text }]);
    try {
      const raw = await post<unknown>("/api/ai/chat", {
        message: text,
        filters,
        context,
      });
      if (requestSession !== session.current) return;
      const result = normalizeAnalystResponse(raw);
      if (Object.keys(result.context).length) setContext(result.context);
      setMessages((m) => [
        ...m,
        { role: "analyst", text: result.answer, result },
      ]);
      if (
        result.intent === "FILTER_COMMAND" ||
        Object.values(result.filters).some(
          (v) => v !== null && v !== undefined && v !== "" && v !== 0,
        )
      )
        applyAction(result.filters);
    } catch {
      if (requestSession !== session.current) return;
      setMessages((m) => [
        ...m,
        {
          role: "analyst",
          text: "AI Analyst could not load. Please retry.",
          retryQuestion: text,
        },
      ]);
    } finally {
      if (requestSession === session.current) setBusy(false);
    }
  }
  function format(key: string, v: unknown) {
    if (key === "month") return monthLabel(v, true);
    if (key.endsWith("_date")) return dateLabel(v);
    if (typeof v !== "number" || !Number.isFinite(v)) return String(v ?? "—");
    if (/percent/.test(key)) return percent(v);
    if (/cost|spend|saving/.test(key)) return money(v);
    return typeof v === "number" ? number(v) : String(v ?? "—");
  }
  const miniTable = (rows: Row[]) => {
    if (!rows.length) return null;
    const keys = [
      "lane",
      "carrier",
      "shipment_id",
      "month",
      "rate_type",
      "potential_saving",
      "actual_spend",
      "optimized_spend",
      "shipment_count",
      "actual_count",
      "recommended_count",
      "total_landed_cost",
      "reason",
    ]
      .filter((k) => k in rows[0])
      .slice(0, 4);
    if (!keys.length) return null;
    return (
      <div className="table-scroll">
        <table className="mini-table">
          <thead>
            <tr>
              {keys.map((k) => (
                <th key={k}>{metricLabel(k)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {keys.map((k) => (
                  <td key={k}>{format(k, r[k])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };
  return (
    <section className="analyst-inline" aria-label="AI Capacity Analyst">
      <header className="dock-header">
        <div>
          <h2>
            <Sparkles size={16} />
            AI Capacity Analyst
          </h2>
          <p>Ask about shipments, lanes, carriers, costs and savings.</p>
        </div>
        <button
          className="icon-button"
          aria-label="Start new chat"
          title="New Chat"
          onClick={newChat}
        >
          <RotateCcw size={16} />
        </button>
        <button
          className="icon-button"
          aria-label="Collapse AI analyst"
          onClick={onClose}
        >
          <PanelRightClose size={18} />
        </button>
      </header>
      <div className="analyst-notice">
        <span className="status-dot" />
        Deterministic analytics · {isDemo ? "DEMO DATA" : "Imported data"}
      </div>
      <div className="chat-body" aria-live="polite">
        {!messages.length && (
          <>
            <div className="analyst-intro">
              <h3>Your backtest, explained.</h3>
              <p>
                Explore the current dashboard scope. Every number comes from the
                analytics backend.
              </p>
            </div>
            <div className="suggestions">
              {suggestions.map((s) => (
                <button key={s} onClick={() => ask(s)}>
                  {s}
                  <ArrowUp size={12} />
                </button>
              ))}
            </div>
          </>
        )}
        {messages.map((m, i) => (
          <div key={i} className={"message " + m.role}>
            <small>
              {m.role === "user"
                ? "YOU"
                : m.role === "action"
                  ? "DASHBOARD"
                  : "CAPACITY ANALYST"}
            </small>
            <p>
              {m.result?.intent === "DATA_PROVENANCE" ? (
                <ProvenanceAnswer text={m.text} />
              ) : (
                m.text
              )}
            </p>
            {m.result && (
              <>
                <div className="metric-mini">
                  {Object.entries(m.result.metrics)
                    .filter(([, v]) => typeof v === "number")
                    .slice(0, 4)
                    .map(([k, v]) => (
                      <div key={k}>
                        <small>{metricLabel(k)}</small>
                        <b>{format(k, v)}</b>
                      </div>
                    ))}
                </div>
                {miniTable(m.result.table)}
                {m.result.chart && (
                  <TrendChart rows={m.result.chart.rows} />
                )}{" "}
                {m.result.data_scope && (
                  <small className="scope">
                    Scope: {dateLabel(m.result.data_scope.start_date)} —{" "}
                    {dateLabel(m.result.data_scope.end_date)} ·{" "}
                    {number(m.result.data_scope.shipment_count)} shipments
                  </small>
                )}
                {Object.keys(m.result.filters).length > 0 &&
                  m.result.intent !== "FILTER_COMMAND" && (
                    <button
                      className="secondary"
                      onClick={() => applyAction(m.result!.filters)}
                    >
                      <SlidersHorizontal size={12} />
                      Apply filters
                    </button>
                  )}
              </>
            )}
            {m.retryQuestion && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => ask(m.retryQuestion!)}
              >
                Retry analyst
              </button>
            )}
          </div>
        ))}
        {busy && (
          <div className="message analyst">
            <span className="pulse" />
            Calculating from historical rows…
          </div>
        )}
        <div ref={bottom} />
      </div>
      {!!messages.length && (
        <div
          className="suggestions suggestions-compact"
          aria-label="Try asking"
        >
          <small>Try asking</small>
          {suggestions.map((s) => (
            <button key={s} disabled={busy} onClick={() => ask(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <textarea
          aria-label="Ask an analytics question"
          placeholder="Ask about your backtest..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask(input);
            }
          }}
        />
        <button
          className="primary"
          aria-label="Send question"
          disabled={busy || !input.trim()}
        >
          <ArrowUp size={17} />
        </button>
      </form>
      <p className="chat-footer">
        Current scope · recorded options · computed results
      </p>
    </section>
  );
}
