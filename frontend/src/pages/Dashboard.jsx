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

  // Inject the unified custom state hook
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
  } = useDashboardData();

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col font-sans">
      {/* 1. Header Navigation */}
      <Header
        onRefresh={refreshData}
        showAddForm={showAddForm}
        onToggleAddForm={() => setShowAddForm(!showAddForm)}
      />

      {/* 2. Main Workspace Layout */}
      <main className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto w-full">
        {/* Left 2 Columns */}
        <div className="lg:col-span-2 flex flex-col space-y-6">
          {/* Slide Form Panel (For admin role only) */}
          {showAddForm && user.role === "admin" && (
            <ProvisioningForm onRegistrationSuccess={refreshData} />
          )}

          {/* Bins Registry Grid */}
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
