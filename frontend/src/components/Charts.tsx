import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import type { Row } from "../types";
import { money, percent, number, monthLabel } from "../services/api";
const colors = ["#007f79", "#9cbdbf", "#172d43"];
export function TrendChart({ rows }: { rows: Row[] }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={rows}
          margin={{ top: 14, right: 18, left: 8, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 4"
            vertical={false}
            stroke="#e6ecef"
          />
          <XAxis
            dataKey="month"
            tickFormatter={(v) => monthLabel(v)}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#6c7f8c", fontSize: 11 }}
          />
          <YAxis
            tickFormatter={(v) => money(v)}
            tickLine={false}
            axisLine={false}
            width={82}
            tick={{ fill: "#6c7f8c", fontSize: 11 }}
          />
          <Tooltip
            formatter={(v) => money(v)}
            labelFormatter={(v) => monthLabel(v, true)}
          />
          <Line
            name="Actual cost"
            dataKey="actual_spend"
            type="monotone"
            stroke="#99a9b1"
            strokeDasharray="4 3"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
          <Line
            name="Optimized cost"
            dataKey="optimized_spend"
            type="monotone"
            stroke="#008b82"
            strokeWidth={2.5}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
export function CarrierChart({ rows }: { rows: Row[] }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 20 }}>
          <CartesianGrid
            strokeDasharray="3 4"
            horizontal={false}
            stroke="#e6ecef"
          />
          <XAxis
            type="number"
            tickFormatter={(v) => money(v)}
            tick={{ fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="carrier"
            width={123}
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip formatter={(v) => money(v)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar
            dataKey="actual_spend"
            name="Actual spend"
            fill="#dbe6e9"
            radius={[0, 3, 3, 0]}
          />
          <Bar
            dataKey="potential_saving"
            name="Savings opportunity"
            fill="#008b82"
            radius={[0, 3, 3, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function RateMix({ rows }: { rows: Row[] }) {
  return (
    <div className="rate-content">
      {["actual", "recommended"].map((kind) => (
        <div className="donut-wrap" key={kind}>
          <h4>{kind === "actual" ? "Actual mix" : "Recommended mix"}</h4>
          <div className="donut">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={rows}
                  dataKey={kind + "_count"}
                  nameKey="rate_type"
                  innerRadius="62%"
                  outerRadius="86%"
                  paddingAngle={3}
                  stroke="none"
                >
                  {rows.map((r, i) => (
                    <Cell key={String(r.rate_type)} fill={colors[i]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => number(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
      <div className="mix-legend">
        {rows.map((r, i) => (
          <div key={String(r.rate_type)}>
            <span>
              <i style={{ background: colors[i] }} />
              {r.rate_type}
            </span>
            <b>
              {percent(r.actual_percent)} <span className="muted">→</span>{" "}
              {percent(r.recommended_percent)}
            </b>
          </div>
        ))}
      </div>
    </div>
  );
}
