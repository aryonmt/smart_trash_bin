// frontend/src/components/HistoryChart.jsx
// -------------------------------------------------------------------------
// Premium HistoryChart Component - Plots neon fill trends and offers actions
// -------------------------------------------------------------------------

import React from "react";
import { BarChart2, Trash2, Calendar } from "lucide-react";
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
  onDeleteBin,
}) {
  const isAuthorizeOverride = userRole === "admin" || userRole === "operator";

  return (
    <section className="bg-slate-900/30 border border-slate-800/80 p-6 rounded-2xl shadow-2xl backdrop-blur-md flex-1 flex flex-col justify-between min-h-[360px] relative overflow-hidden transition-all duration-300">
      {/* Background design glow */}
      <div className="absolute -bottom-20 -left-10 w-44 h-44 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* Header section of the chart panel */}
      <div className="flex justify-between items-center mb-6 border-b border-slate-800/40 pb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
            <BarChart2 className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-sm font-black tracking-widest text-slate-300 uppercase">
              Sensory History Chart
            </h2>
            {selectedBin && (
              <span className="text-[10px] text-slate-500 font-bold tracking-wider">
                Active Node:{" "}
                <span className="text-emerald-400/80 font-mono">
                  {selectedBin.bin_id}
                </span>
              </span>
            )}
          </div>
        </div>

        {/* Admin actions toolbar */}
        {selectedBin && isAuthorizeOverride && (
          <div className="flex items-center space-x-2">
            {userRole === "admin" && (
              <button
                onClick={() => onDeleteBin(selectedBin.bin_id)}
                className="flex items-center space-x-1.5 bg-red-500/10 hover:bg-red-500 border border-red-500/20 hover:border-red-500/40 text-red-400 hover:text-white px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-red-500/5 hover:shadow-red-500/15"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Bin</span>
              </button>
            )}
            <button
              onClick={() => onManualEmpty(selectedBin.bin_id)}
              className="flex items-center space-x-1.5 bg-emerald-500/10 hover:bg-emerald-500 border border-emerald-500/20 hover:border-emerald-500/40 text-emerald-400 hover:text-white px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-emerald-500/5 hover:shadow-emerald-500/15"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Force Reset Bin</span>
            </button>
          </div>
        )}
      </div>

      {/* Rest of the chart remains same... */}

      {/* Chart Area or Empty State */}
      {selectedBin ? (
        history.length > 0 ? (
          <div className="h-64 w-full relative z-10">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={history}
                margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b/40" />
                <XAxis
                  dataKey="time"
                  tickFormatter={(t) => new Date(t).toLocaleTimeString()}
                  stroke="#64748b"
                  fontSize={10}
                  fontWeight="600"
                  tickLine={false}
                  dy={8}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="#64748b"
                  fontSize={10}
                  fontWeight="600"
                  tickLine={false}
                  dx={-8}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.9)",
                    borderColor: "rgba(51, 65, 85, 0.8)",
                    borderRadius: "16px",
                    backdropFilter: "blur(12px)",
                    boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.3)",
                  }}
                  labelFormatter={(l) => new Date(l).toLocaleString()}
                  formatter={(value) => [`${value}%`, "Fill Level"]}
                />
                <Area
                  type="monotone"
                  dataKey="fill_percent"
                  stroke="#10b981"
                  strokeWidth={2.5}
                  fillOpacity={1}
                  fill="url(#colorFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center py-16 text-slate-500 font-semibold text-xs tracking-wider flex items-center justify-center space-x-2">
            <span className="h-2 w-2 bg-slate-500 rounded-full animate-ping"></span>
            <span>Retrieving telemetry time-series logs...</span>
          </div>
        )
      ) : (
        <div className="text-center py-20 text-slate-500 flex flex-col items-center justify-center h-full">
          <div className="p-4 bg-slate-950/40 border border-slate-800/40 rounded-2xl mb-4">
            <Calendar className="h-8 w-8 text-slate-700 animate-pulse" />
          </div>
          <span className="text-xs font-bold tracking-widest uppercase text-slate-600">
            No Node Selected
          </span>
          <span className="text-[10px] text-slate-600 mt-1 max-w-xs leading-relaxed">
            Select an active waste bin card from the fleet grid above to project
            its telemetry history.
          </span>
        </div>
      )}
    </section>
  );
}
