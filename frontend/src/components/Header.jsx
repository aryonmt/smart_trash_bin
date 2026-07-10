// frontend/src/components/Header.jsx
// -------------------------------------------------------------------------
// Premium Glassmorphism Header Component with Micro-Interactions
// -------------------------------------------------------------------------

import React from "react";
import { Trash2, User, RefreshCw, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Header({ onRefresh, showAddForm, onToggleAddForm }) {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <header className="bg-slate-900/60 border-b border-slate-800/50 p-4 flex justify-between items-center shadow-xl backdrop-blur-xl sticky top-0 z-50">
      <div className="flex items-center space-x-3 group">
        <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 transition-all duration-300 group-hover:bg-emerald-500/20 group-hover:scale-105">
          <Trash2 className="h-6 w-6 text-emerald-400" />
        </div>
        <h1 className="text-lg font-black tracking-widest bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent uppercase">
          Sensor Grid
        </h1>
      </div>

      <div className="flex items-center space-x-4">
        {user.role === "admin" && (
          <button
            onClick={onToggleAddForm}
            className={`px-4 py-2 rounded-xl transition-all duration-300 text-xs font-bold shadow-md transform hover:-translate-y-0.5 active:translate-y-0 ${
              showAddForm
                ? "bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700"
                : "bg-emerald-500 hover:bg-emerald-600 text-white shadow-emerald-500/10 hover:shadow-emerald-500/20"
            }`}
          >
            {showAddForm ? "Close Panel" : "+ Register New Bin"}
          </button>
        )}

        <div className="flex items-center space-x-2.5 bg-slate-950/40 px-3.5 py-2 rounded-xl border border-slate-800/60">
          <div className="h-2 w-2 rounded-full bg-emerald-400 animate-ping"></div>
          <User className="h-4 w-4 text-emerald-400" />
          <span className="text-xs font-bold tracking-wider text-slate-300">
            {user.username}{" "}
            <span className="text-slate-500 font-medium text-[10px] uppercase ml-1">
              ({user.role})
            </span>
          </span>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center space-x-2 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700/40 text-slate-300 px-3.5 py-2 rounded-xl transition-all duration-200 text-xs font-bold transform hover:-translate-y-0.5 active:translate-y-0"
        >
          <RefreshCw className="h-3.5 w-3.5 animate-spin-slow" />
          <span>Refresh</span>
        </button>

        <button
          onClick={logout}
          className="flex items-center space-x-1.5 bg-red-500/10 hover:bg-red-500 border border-red-500/20 text-red-400 hover:text-white px-3.5 py-2 rounded-xl transition-all duration-200 text-xs font-bold transform hover:-translate-y-0.5 active:translate-y-0 shadow-lg shadow-red-500/5 hover:shadow-red-500/20"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
