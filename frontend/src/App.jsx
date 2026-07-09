// frontend/src/App.jsx
// -------------------------------------------------------------------------
// Smart Waste Bin - Multi-Page Protected routing with JWT auth & RBAC UI
// -------------------------------------------------------------------------

import React, { useState, useEffect } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";
import {
  Trash2,
  AlertTriangle,
  Wifi,
  WifiOff,
  RefreshCw,
  BarChart2,
  CheckCircle,
  LogIn,
  LogOut,
  User,
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

// --- Authentication State Guard ---
function ProtectedRoute({ children }) {
  const token = sessionStorage.getItem("token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// --- Page Component: Login Screen ---
function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (sessionStorage.getItem("token")) {
      navigate("/");
    }
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error("Invalid username or password credentials");
      }

      const data = await response.json();
      sessionStorage.setItem("token", data.access_token);
      sessionStorage.setItem("role", data.role);
      sessionStorage.setItem("username", data.username);

      onLoginSuccess();
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 p-8 rounded-2xl shadow-2xl backdrop-blur-md">
        <div className="flex flex-col items-center mb-6">
          <Trash2 className="h-12 w-12 text-emerald-500 mb-2" />
          <h2 className="text-2xl font-bold tracking-wider text-emerald-400">
            Smart Waste City Login
          </h2>
          <p className="text-gray-500 text-xs mt-1">
            Authorized municipal control personnel only
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 text-sm p-3 rounded-lg mb-4 text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-400 text-xs font-semibold mb-1">
              USERNAME
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. admin"
              className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-sm focus:outline-none focus:border-emerald-500 text-white"
            />
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold mb-1">
              PASSWORD
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-gray-950 border border-gray-800 rounded-lg p-3 text-sm focus:outline-none focus:border-emerald-500 text-white"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/50 text-white font-bold py-3 rounded-lg transition duration-200 flex items-center justify-center space-x-2 text-sm shadow-lg shadow-emerald-500/10"
          >
            <LogIn className="h-4 w-4" />
            <span>
              {loading ? "Authenticating Session..." : "Secure Login"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
}

// --- Page Component: Dashboard Layout ---
function Dashboard() {
  // Provisioning form states
  const [showAddForm, setShowAddForm] = useState(false);
  const [newBinId, setNewBinId] = useState("");
  const [newZoneId, setNewZoneId] = useState("");
  const [newDepth, setNewDepth] = useState(150);
  const [newLabel, setNewLabel] = useState("");
  const [newLat, setNewLat] = useState("");
  const [newLng, setNewLng] = useState("");
  const [formSuccess, setFormSuccess] = useState("");
  const [formError, setFormError] = useState("");
  const [bins, setBins] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedBin, setSelectedBin] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const userRole = sessionStorage.getItem("role");
  const userName = sessionStorage.getItem("username");

  const getHeaders = () => {
    const token = sessionStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  const handleLogout = () => {
    sessionStorage.clear();
    navigate("/login");
  };

  const fetchData = async () => {
    try {
      const [binsRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/bins`, { headers: getHeaders() }),
        fetch(`${API_BASE_URL}/api/alerts`, { headers: getHeaders() }),
      ]);

      if (binsRes.status === 401 || alertsRes.status === 401) {
        handleLogout();
        return;
      }

      const binsData = await binsRes.json();
      setBins(binsData);

      // Alerts endpoint returns 403 for restricted roles (drivers), check safety
      if (alertsRes.ok) {
        const alertsData = await alertsRes.json();
        setAlerts(alertsData);
      }
    } catch (err) {
      console.error("Data ingestion polling failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (binId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/bins/${binId}/history`, {
        headers: getHeaders(),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      const data = await res.json();
      setHistory(data.reverse());
    } catch (err) {
      console.error("Error fetching bin time-series data:", err);
    }
  };

  const acknowledgeAlert = async (alertId) => {
    try {
      await fetch(`${API_BASE_URL}/api/alerts/${alertId}/acknowledge`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({ operator_name: userName }),
      });
      fetchData();
    } catch (err) {
      console.error("Failed to acknowledge warning:", err);
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
        headers: getHeaders(),
      });
      if (res.ok) {
        fetchData();
        fetchHistory(binId);
      }
    } catch (err) {
      console.error("Failed manual empty process:", err);
    }
  };
  const handleRegisterBin = async (e) => {
    e.preventDefault();
    setFormError("");
    setFormSuccess("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/bins`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({
          bin_id: newBinId,
          zone_id: newZoneId,
          bin_depth_cm: parseFloat(newDepth),
          label: newLabel || null,
          latitude: newLat ? parseFloat(newLat) : null,
          longitude: newLng ? parseFloat(newLng) : null,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Registration failed");
      }

      setFormSuccess(`Bin ${newBinId} successfully provisioned!`);
      setNewBinId("");
      setNewZoneId("");
      setNewLabel("");
      setNewLat("");
      setNewLng("");
      fetchData(); // Refresh bin grid instantly
    } catch (err) {
      setFormError(err.message);
    }
  };
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
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

        <div className="flex items-center space-x-4">
          {userRole === "admin" && (
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="bg-emerald-500 hover:bg-emerald-600 text-white px-3.5 py-1.5 rounded-lg transition text-xs font-bold"
            >
              {showAddForm ? "Close Panel" : "+ Register New Bin"}
            </button>
          )}
          <div className="flex items-center space-x-2 bg-gray-950/60 px-3.5 py-1.5 rounded-lg border border-gray-850">
            <User className="h-4 w-4 text-emerald-500" />
            <span className="text-xs font-semibold">
              {userName} ({userRole.toUpperCase()})
            </span>
          </div>

          <button
            onClick={fetchData}
            className="flex items-center space-x-2 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition text-xs font-semibold"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleLogout}
            className="flex items-center space-x-1.5 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white px-3.5 py-1.5 rounded-lg transition text-xs font-bold"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Body */}
      {/* Main Body Layout */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto w-full">
        {/* Left 2 Columns: Provisioning, Live Bins and History Chart */}
        <div className="lg:col-span-2 flex flex-col space-y-6">
          {/* Provisioning Slide Form Panel (Renders only if toggled by admin) */}
          {showAddForm && userRole === "admin" && (
            <section className="bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl transition-all duration-300">
              <h3 className="text-emerald-400 font-bold text-lg mb-4 flex items-center gap-2">
                <Trash2 className="h-5 w-5" />
                Provision New Smart Bin
              </h3>

              {formError && (
                <div className="bg-red-500/10 border border-red-500 text-red-400 text-xs p-2.5 rounded-lg mb-4 text-center">
                  {formError}
                </div>
              )}
              {formSuccess && (
                <div className="bg-emerald-500/10 border border-emerald-500 text-emerald-400 text-xs p-2.5 rounded-lg mb-4 text-center">
                  {formSuccess}
                </div>
              )}

              <form
                onSubmit={handleRegisterBin}
                className="grid grid-cols-1 md:grid-cols-3 gap-4"
              >
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    BIN ID *
                  </label>
                  <input
                    type="text"
                    required
                    value={newBinId}
                    onChange={(e) => setNewBinId(e.target.value)}
                    placeholder="e.g. bin-0143"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    ZONE ID *
                  </label>
                  <input
                    type="text"
                    required
                    value={newZoneId}
                    onChange={(e) => setNewZoneId(e.target.value)}
                    placeholder="e.g. district-7"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    BIN DEPTH (CM) *
                  </label>
                  <input
                    type="number"
                    required
                    value={newDepth}
                    onChange={(e) => setNewDepth(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    LABEL (LOCATION)
                  </label>
                  <input
                    type="text"
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    placeholder="e.g. Central Library Corner"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    LATITUDE
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={newLat}
                    onChange={(e) => setNewLat(e.target.value)}
                    placeholder="e.g. 35.7001"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-gray-400 text-[10px] font-bold mb-1">
                    LONGITUDE
                  </label>
                  <input
                    type="number"
                    step="any"
                    value={newLng}
                    onChange={(e) => setNewLng(e.target.value)}
                    placeholder="e.g. 51.4002"
                    className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="md:col-span-3 flex justify-end pt-2">
                  <button
                    type="submit"
                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-2.5 px-6 rounded-lg text-xs transition duration-200 shadow-md shadow-emerald-500/10"
                  >
                    Authorize and Register Bin
                  </button>
                </div>
              </form>
            </section>
          )}

          {/* Bins Grid Section */}
          <section>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Trash2 className="h-5 w-5 text-emerald-500" />
              Live Bins Registry ({bins.length})
            </h2>

            {loading ? (
              <div className="bg-gray-900 p-8 rounded-xl border border-gray-800 text-center text-gray-400">
                Fetching fleet data...
              </div>
            ) : bins.length === 0 ? (
              <div className="bg-gray-900 p-8 rounded-xl border border-gray-800 text-center text-gray-500">
                No active bins reported in scope.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {bins.map((bin) => {
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
                        <div>
                          {isOnline ? (
                            <span className="flex items-center text-[10px] text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full font-semibold">
                              <Wifi className="h-3 w-3 mr-1" /> Online
                            </span>
                          ) : (
                            <span className="flex items-center text-[10px] text-gray-400 bg-gray-500/10 px-2 py-0.5 rounded-full font-semibold">
                              <WifiOff className="h-3 w-3 mr-1" /> Offline
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Progress */}
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
                            Emptied
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
                Sensory History:{" "}
                {selectedBin ? selectedBin.bin_id : "Select a bin"}
              </h2>
              {selectedBin &&
                (userRole === "admin" || userRole === "operator") && (
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
                  Retrieving historical entries...
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
        {userRole !== "driver" && (
          <div className="flex flex-col space-y-6">
            <section className="bg-gray-900 border border-gray-800 p-5 rounded-2xl flex-1 flex flex-col">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-400">
                <AlertTriangle className="h-5 w-5" />
                Active Warnings ({alerts.length})
              </h2>

              {alerts.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center py-12 text-gray-500">
                  <CheckCircle className="h-12 w-12 text-emerald-500/20 mb-3" />
                  <span className="text-emerald-500 font-medium">
                    All systems green
                  </span>
                </div>
              ) : (
                <div className="space-y-3 overflow-y-auto flex-1 max-h-[500px] pr-1">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="p-4 bg-gray-950 border border-gray-800 rounded-xl flex flex-col justify-between"
                    >
                      <div className="flex items-start space-x-2">
                        <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <h4 className="font-bold text-sm">
                            Critical Threshold Triggered
                          </h4>
                          <span className="text-xs text-gray-400 font-mono">
                            Bin: {alert.bin_id}
                          </span>
                        </div>
                      </div>

                      <div className="mt-3 pt-3 border-t border-gray-850 flex justify-between items-center text-[11px] text-gray-400">
                        <span>
                          Triggered:{" "}
                          {new Date(alert.triggered_at).toLocaleTimeString()}
                        </span>
                        {alert.acknowledged_by ? (
                          <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-medium">
                            Ack'd: {alert.acknowledged_by}
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
        )}
      </main>
    </div>
  );
}

// --- Main Router Composition Bootstrapper ---
export default function App() {
  const [authKey, setAuthKey] = useState(0);
  const triggerAuthRefresh = () => setAuthKey((prev) => prev + 1);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<Login onLoginSuccess={triggerAuthRefresh} />}
        />
        <Route
          path="/"
          element={
            <ProtectedRoute key={authKey}>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
