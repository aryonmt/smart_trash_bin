// frontend/src/hooks/useDashboardData.js
// -------------------------------------------------------------------------
// Decoupled, optimized dashboard data polling hook with stable dependencies
// -------------------------------------------------------------------------

import { useState, useEffect, useCallback } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function useDashboardData() {
  const [bins, setBins] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedBin, setSelectedBin] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const { logout } = useAuth();

  // Stable callback for fetching historical time-series
  const fetchHistory = useCallback(async (binId) => {
    try {
      const data = await api.getBinHistory(binId);
      setHistory(data.reverse());
    } catch (err) {
      console.error("Error fetching bin history logs:", err);
    }
  }, []);

  // Stable callback for fetching fleet data (Does NOT depend on selectedBin)
  const fetchFleetData = useCallback(async () => {
    try {
      const [binsData, alertsData] = await Promise.all([
        api.getBins(),
        api.getAlerts().catch((err) => {
          if (err.message.includes("403")) return [];
          throw err;
        }),
      ]);

      setBins(binsData);
      setAlerts(alertsData);
    } catch (err) {
      console.error("Fleet live polling cycle failed:", err);
      if (err.message.includes("401") || err.message.includes("credentials")) {
        logout();
      }
    } finally {
      setLoading(false);
    }
  }, [logout]);

  const acknowledgeAlert = async (alertId, operatorName) => {
    try {
      await api.acknowledgeAlert(alertId, operatorName);
      await fetchFleetData();
    } catch (err) {
      console.error("Failed to acknowledge alert:", err);
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
      await api.manualEmptyBin(binId);
      await fetchFleetData();
      if (selectedBin?.bin_id === binId) {
        await fetchHistory(binId);
      }
    } catch (err) {
      console.error("Failed manual empty override transaction:", err);
    }
  };

  const handleDeleteBin = async (binId) => {
    if (
      !window.confirm(
        `Are you sure you want to permanently delete bin ${binId}? This will erase all its history and alerts!`,
      )
    ) {
      return;
    }
    try {
      await api.deleteBin(binId);
      setSelectedBin(null); // Clear selected bin on deletion
      await fetchFleetData();
    } catch (err) {
      console.error("Failed to delete bin:", err);
    }
  };

  // Polling Loop 1: Fleet metadata polling (Runs stably every 3 seconds)
  useEffect(() => {
    fetchFleetData();
    const interval = setInterval(fetchFleetData, 3000);
    return () => clearInterval(interval);
  }, [fetchFleetData]);

  // Polling Loop 2: Selected Bin History polling (Runs only if a bin is selected)
  useEffect(() => {
    if (!selectedBin) {
      setHistory([]);
      return;
    }

    fetchHistory(selectedBin.bin_id);
    const interval = setInterval(() => {
      fetchHistory(selectedBin.bin_id);
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedBin, fetchHistory]);

  const selectBin = (bin) => {
    setSelectedBin(bin);
  };

  return {
    bins,
    alerts,
    selectedBin,
    history,
    loading,
    refreshData: fetchFleetData,
    selectBin,
    acknowledgeAlert,
    handleManualEmpty,
    handleDeleteBin,
  };
}
