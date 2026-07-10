// frontend/src/components/Header.jsx
// -------------------------------------------------------------------------
// Header Component - Renders user details, refresh action and logout
// -------------------------------------------------------------------------

import React from "react";
import { Trash2, User, RefreshCw, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Header({ onRefresh, showAddForm, onToggleAddForm }) {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <header className="bg-gray-900 border-b border-gray-800 p-4 flex justify-between items-center shadow-lg">
      <div className="flex items-center space-x-3">
        <Trash2 className="h-8 w-8 text-emerald-500" />
        <h1 className="text-xl font-bold tracking-wider">
          Smart Waste City Network
        </h1>
      </div>

      <div className="flex items-center space-x-4">
        {user.role === "admin" && (
          <button
            onClick={onToggleAddForm}
            className="bg-emerald-500 hover:bg-emerald-600 text-white px-3.5 py-1.5 rounded-lg transition text-xs font-bold shadow-md"
          >
            {showAddForm ? "Close Panel" : "+ Register New Bin"}
          </button>
        )}

        <div className="flex items-center space-x-2 bg-gray-950/60 px-3.5 py-1.5 rounded-lg border border-gray-850">
          <User className="h-4 w-4 text-emerald-500" />
          <span className="text-xs font-semibold">
            {user.username} ({user.role.toUpperCase()})
          </span>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center space-x-2 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition text-xs font-semibold"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh</span>
        </button>

        <button
          onClick={logout}
          className="flex items-center space-x-1.5 bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white px-3.5 py-1.5 rounded-lg transition text-xs font-bold"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
