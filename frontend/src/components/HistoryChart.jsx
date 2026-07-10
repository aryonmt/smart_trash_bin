// frontend/src/components/HistoryChart.jsx
// -------------------------------------------------------------------------
// HistoryChart Component - Plots historical fill trend and provides override action
// -------------------------------------------------------------------------

import React from "react";
import { BarChart2, Trash2 } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export default function HistoryChart({
  selectedBin,
  history,
  userRole,
  onManualEmpty,
}) {
  const isAuthorizeOverride = userRole === "admin" || userRole === "operator";

  return (
    <section className="bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl flex-1 flex flex-col justify-between min-h-[300px]">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <BarChart2 className="h-5 w-5 text-emerald-500" />
          Sensory History: {selectedBin ? selectedBin.bin_id : "Select a bin"}
        </h2>
        {selectedBin && isAuthorizeOverride && (
          <button
            onClick={() => onManualEmpty(selectedBin.bin_id)}
            className="flex items-center space-x-1.5 bg-emerald-500/10 hover:bg-emerald-500 hover:text-white text-emerald-400 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition shadow-md shadow-emerald-500/5"
          >
            <Trash2 className="h-4 w-4" />
            <span>Mark Bin as Emptied</span>
          </button>
        )}
      </div>

      {selectedBin ? (
        history.length > 0 ? (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={history}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis
                  dataKey="time"
                  tickFormatter={(t) => new Date(t).toLocaleTimeString()}
                  stroke="#9ca3af"
                  fontSize={11}
                />
                <YAxis domain={[0, 100]} stroke="#9ca3af" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#111827",
                    borderColor: "#374151",
                    borderRadius: "8px",
                  }}
                  labelFormatter={(l) => new Date(l).toLocaleString()}
                  formatter={(value) => [`${value}%`, "Fill Level"]}
                />
                <Area
                  type="monotone"
                  dataKey="fill_percent"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            Retrieving historical entries...
          </div>
        )
      ) : (
        <div className="text-center py-12 text-gray-500 flex flex-col items-center justify-center h-full">
          <Trash2 className="h-10 w-10 text-gray-700 mb-2" />
          <span>
            Click on any bin registry card to view real-time fill trend lines
          </span>
        </div>
      )}
    </section>
  );
}
