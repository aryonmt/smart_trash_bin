// frontend/src/pages/Dashboard.jsx
// -------------------------------------------------------------------------
// Dashboard Page Component - Orchestrates all sub-components and layouts
// -------------------------------------------------------------------------

import React, { useState } from "react";
import { Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import useDashboardData from "../hooks/useDashboardData";

import Header from "../components/Header";
import ProvisioningForm from "../components/ProvisioningForm";
import BinCard from "../components/BinCard";
import HistoryChart from "../components/HistoryChart";
import AlertList from "../components/AlertList";

export default function Dashboard() {
  const { user } = useAuth();
  const [showAddForm, setShowAddForm] = useState(false);

  // Injected and destructured handleDeleteBin handler from custom hook
  const {
    bins,
    alerts,
    selectedBin,
    history,
    loading,
    refreshData,
    selectBin,
    acknowledgeAlert,
    handleManualEmpty,
    handleDeleteBin,
  } = useDashboardData();

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-zinc-950 flex flex-col font-sans relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute top-10 right-10 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-10 left-10 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none"></div>

      {/* 1. Header Navigation */}
      <Header
        onRefresh={refreshData}
        showAddForm={showAddForm}
        onToggleAddForm={() => setShowAddForm(!showAddForm)}
      />

      {/* 2. Main Workspace Layout */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto w-full relative z-10">
        {/* Left 2 Columns */}
        <div className="lg:col-span-2 flex flex-col space-y-6">
          {/* Slide Form Panel (For admin role only) */}
          {showAddForm && user.role === "admin" && (
            <ProvisioningForm onRegistrationSuccess={refreshData} />
          )}

          {/* Bins Registry Grid */}
          <section>
            <h2 className="text-sm font-black tracking-widest text-slate-300 mb-4 flex items-center gap-2 uppercase">
              <Trash2 className="h-4 w-4 text-emerald-400" />
              Live Bins Registry ({bins.length})
            </h2>

            {loading ? (
              <div className="bg-slate-900/30 border border-slate-800/80 p-12 rounded-3xl text-center text-slate-500 font-semibold text-xs tracking-wider flex items-center justify-center space-x-2 backdrop-blur-md">
                <span className="h-2 w-2 bg-emerald-400 rounded-full animate-ping"></span>
                <span>Fetching grid data from sensor fleet...</span>
              </div>
            ) : bins.length === 0 ? (
              <div className="bg-slate-900/20 border border-slate-800/60 p-12 rounded-3xl text-center text-slate-500 font-bold tracking-widest text-xs uppercase">
                No active bins reported in scope
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {bins.map((bin) => (
                  <BinCard
                    key={bin.bin_id}
                    bin={bin}
                    selectedBin={selectedBin}
                    onSelect={selectBin}
                  />
                ))}
              </div>
            )}
          </section>

          {/* History Time-Series Chart */}
          <HistoryChart
            selectedBin={selectedBin}
            history={history}
            userRole={user.role}
            onManualEmpty={handleManualEmpty}
            onDeleteBin={handleDeleteBin}
          />
        </div>

        {/* Right 1 Column: Alerts Management */}
        {user.role !== "driver" && (
          <div className="flex flex-col space-y-6">
            <AlertList
              alerts={alerts}
              userRole={user.role}
              onAcknowledge={(alertId) =>
                acknowledgeAlert(alertId, user.username)
              }
            />
          </div>
        )}
      </main>
    </div>
  );
}
