// frontend/src/pages/Login.jsx
// -------------------------------------------------------------------------
// Premium Neon-Dark Login Page Component with Glassmorphism UI
// -------------------------------------------------------------------------

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, LogIn, ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/");
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await api.login(username, password);
      login(data);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-zinc-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Glowing background ambient rings */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

      <div className="w-full max-w-md bg-slate-900/40 border border-slate-800/80 p-8 rounded-3xl shadow-2xl backdrop-blur-xl relative z-10">
        <div className="flex flex-col items-center mb-8">
          <div className="p-4 bg-emerald-500/10 rounded-2xl border border-emerald-500/20 mb-4 shadow-inner">
            <Trash2 className="h-10 w-10 text-emerald-400 animate-pulse" />
          </div>
          <h2 className="text-3xl font-extrabold tracking-wider bg-gradient-to-r from-emerald-400 to-teal-200 bg-clip-text text-transparent">
            MUNICIPAL SENSOR
          </h2>
          <p className="text-slate-500 text-xs font-semibold mt-2 tracking-widest uppercase">
            Smart Waste Network
          </p>
        </div>

        {error && (
          <div className="bg-red-500/5 border border-red-500/20 text-red-400 text-xs p-3.5 rounded-xl mb-6 flex items-center space-x-2 backdrop-blur-md">
            <ShieldAlert className="h-4 w-4 flex-shrink-0" />
            <span className="font-semibold">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
              Username
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter administrator ID"
              className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3.5 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/20 transition-all placeholder:text-slate-600 font-medium"
            />
          </div>

          <div>
            <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter secure password"
              className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3.5 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/20 transition-all placeholder:text-slate-600 font-medium"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/40 text-white font-bold py-3.5 rounded-xl transition-all duration-300 flex items-center justify-center space-x-2 text-xs shadow-lg shadow-emerald-500/10 hover:shadow-emerald-500/20 transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <LogIn className="h-4 w-4" />
            <span className="tracking-widest uppercase">
              {loading ? "Authorizing..." : "Establish Connection"}
            </span>
          </button>
        </form>
      </div>
    </div>
  );
}
