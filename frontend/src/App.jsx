// frontend/src/App.jsx
// -------------------------------------------------------------------------
// Live Smart Waste Bin Dashboard - React Single Page Application
// -------------------------------------------------------------------------

import React, { useState, useEffect } from "react";
import {
  Trash2,
  AlertTriangle,
  Wifi,
  WifiOff,
  RefreshCw,
  BarChart2,
  CheckCircle,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const API_BASE_URL = `http://${window.location.hostname}:8000`;

export default function App() {
  const [bins, setBins] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedBin, setSelectedBin] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const binsRes = await fetch(`${API_BASE_URL}/api/bins`);
      const binsData = await binsRes.json();
      setBins(binsData);

      const alertsRes = await fetch(`${API_BASE_URL}/api/alerts?status=open`);
      const alertsData = await alertsRes.json();
      setAlerts(alertsData);

      // If a bin was selected, refresh its history as well
      if (selectedBin) {
        fetchHistory(selectedBin.bin_id);
      }
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (binId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/bins/${binId}/history`);
      const data = await res.json();
      // Reverse history so oldest data is on the left
      setHistory(data.reverse());
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      await fetch(`${API_BASE_URL}/api/alerts/${alertId}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator_name: "Municipal Control Center" }),
      });
      fetchData();
    } catch (err) {
      console.error("Error acknowledging alert:", err);
    }
  };

  const handleManualEmpty = async (binId) => {
    if (
      !window.confirm(
        `Are you sure you want to manually mark ${binId} as emptied?`,
      )
    ) {
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/bins/${binId}/empty`, {
        method: "POST",
      });
      if (res.ok) {
        // Refresh dashboard states instantly
        fetchData();
        fetchHistory(binId);
      }
    } catch (err) {
      console.error("Error manual emptying bin:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Auto-refresh every 3 seconds
    return () => clearInterval(interval);
  }, [selectedBin]);

  const selectBin = (bin) => {
    setSelectedBin(bin);
    fetchHistory(bin.bin_id);
  };

  const getFillColor = (pct) => {
    if (pct >= 80) return "bg-red-500 text-red-500 border-red-500";
    if (pct >= 50) return "bg-yellow-500 text-yellow-500 border-yellow-500";
    return "bg-green-500 text-green-500 border-green-500";
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 p-4 flex justify-between items-center shadow-lg">
        <div className="flex items-center space-x-3">
          <Trash2 className="h-8 w-8 text-emerald-500" />
          <h1 className="text-xl font-bold tracking-wider">
            Smart Waste City Network
          </h1>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center space-x-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg transition"
        >
          <RefreshCw className="h-4 w-4" />
          <span className="text-sm">Refresh Data</span>
        </button>
      </header>

      {/* Main Content Dashboard */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto w-full">
        {/* Left 2 Columns: Bins and History */}
        <div className="lg:col-span-2 flex flex-col space-y-6">
          {/* Section: Bins Grid */}
          <section>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-emerald-500" />
              Live Bins Registry ({bins.length})
            </h2>

            {loading ? (
              <div className="bg-gray-900 p-8 rounded-xl border border-gray-800 text-center text-gray-400">
                Loading fleet data...
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {bins.map((bin) => {
                  const isHigh = bin.current_fill_pct >= 80;
                  const isOnline = bin.status === "online";
                  return (
                    <div
                      key={bin.bin_id}
                      onClick={() => selectBin(bin)}
                      className={`p-4 rounded-xl border transition cursor-pointer hover:scale-[1.02] flex flex-col justify-between h-44 ${
                        selectedBin?.bin_id === bin.bin_id
                          ? "bg-gray-800 border-emerald-500"
                          : "bg-gray-900 border-gray-800"
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-bold text-lg">{bin.bin_id}</h3>
                          <span className="text-xs text-gray-400 font-medium px-2 py-0.5 bg-gray-800 rounded">
                            {bin.zone_id}
                          </span>
                        </div>
                        <div className="flex items-center space-x-1.5">
                          {isOnline ? (
                            <span className="flex items-center text-xs text-green-400 bg-green-500/10 px-2.5 py-0.5 rounded-full font-semibold">
                              <Wifi className="h-3.5 w-3.5 mr-1" /> Online
                            </span>
                          ) : (
                            <span className="flex items-center text-xs text-gray-400 bg-gray-500/10 px-2.5 py-0.5 rounded-full font-semibold">
                              <WifiOff className="h-3.5 w-3.5 mr-1" /> Offline
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="my-3">
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">Fill level</span>
                          <span
                            className={`font-bold ${getFillColor(bin.current_fill_pct).split(" ")[1]}`}
                          >
                            {bin.current_fill_pct !== null
                              ? `${bin.current_fill_pct}%`
                              : "0%"}
                          </span>
                        </div>
                        <div className="w-full bg-gray-800 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${getFillColor(bin.current_fill_pct).split(" ")[0]}`}
                            style={{ width: `${bin.current_fill_pct || 0}%` }}
                          ></div>
                        </div>
                      </div>

                      <div className="text-[11px] text-gray-400 flex justify-between">
                        <span>
                          Last Update:{" "}
                          {bin.last_reading_at
                            ? new Date(bin.last_reading_at).toLocaleTimeString()
                            : "N/A"}
                        </span>
                        {bin.last_emptied_at && (
                          <span className="text-emerald-400 font-medium">
                            Emptied recently
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Section: Chart Area */}
          <section className="bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl flex-1 flex flex-col justify-between min-h-[300px]">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <BarChart2 className="h-5 w-5 text-emerald-500" />
                Sensory History Chart:{" "}
                {selectedBin
                  ? selectedBin.bin_id
                  : "Select a bin from registry"}
              </h2>
              {selectedBin && (
                <button
                  onClick={() => handleManualEmpty(selectedBin.bin_id)}
                  className="flex items-center space-x-1.5 bg-emerald-500/10 hover:bg-emerald-500 hover:text-white text-emerald-400 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition shadow-md"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Mark Bin as Emptied</span>
                </button>
              )}
            </div>

            {selectedBin ? (
              // Inside remains exactly same as before (history plotting)
              history.length > 0 ? (
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={history}
                      margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient
                          id="colorFill"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#10b981"
                            stopOpacity={0.4}
                          />
                          <stop
                            offset="95%"
                            stopColor="#10b981"
                            stopOpacity={0}
                          />
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
                  Retrieving historical time-series entries...
                </div>
              )
            ) : (
              <div className="text-center py-12 text-gray-500 flex flex-col items-center justify-center h-full">
                <Trash2 className="h-10 w-10 text-gray-700 mb-2" />
                <span>
                  Click on any bin registry card to view real-time fill trend
                  lines
                </span>
              </div>
            )}
          </section>
        </div>

        {/* Right 1 Column: Alerts Management */}
        <div className="flex flex-col space-y-6">
          <section className="bg-gray-900 border border-gray-800 p-5 rounded-2xl flex-1 flex flex-col">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-400">
              <AlertTriangle className="h-5 w-5" />
              Active System Warnings ({alerts.length})
            </h2>

            {alerts.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-12 text-gray-500">
                <CheckCircle className="h-12 w-12 text-emerald-500/20 mb-3" />
                <span className="text-emerald-500 font-medium">
                  All systems green
                </span>
                <span className="text-xs text-gray-600 mt-1">
                  No active bin high fill thresholds breached.
                </span>
              </div>
            ) : (
              <div className="space-y-3 overflow-y-auto flex-1 max-h-[500px] pr-1">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="p-4 bg-gray-950 border border-gray-800 rounded-xl flex flex-col justify-between"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex items-start space-x-2">
                        <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="font-bold text-sm">
                            Critical Threshold Triggered
                          </h4>
                          <span className="text-xs text-gray-400 font-mono">
                            Bin ID: {alert.bin_id}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-gray-850 flex justify-between items-center text-[11px] text-gray-400">
                      <span>
                        Triggered:{" "}
                        {new Date(alert.triggered_at).toLocaleTimeString()}
                      </span>

                      {alert.acknowledged_by ? (
                        <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-medium">
                          Ack'd
                        </span>
                      ) : (
                        <button
                          onClick={() => acknowledgeAlert(alert.id)}
                          className="bg-red-500/10 hover:bg-red-500 hover:text-white text-red-400 px-3 py-1 rounded text-xs font-semibold transition"
                        >
                          Acknowledge
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
