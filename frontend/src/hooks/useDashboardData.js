// frontend/src/hooks/useDashboardData.js
// -------------------------------------------------------------------------
// Custom React Hook encapsulating dashboard state, polling and data fetching
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

  const fetchHistory = useCallback(async (binId) => {
    try {
      const data = await api.getBinHistory(binId);
      // Reverse so oldest data point is plotted first on the left
      setHistory(data.reverse());
    } catch (err) {
      console.error("Error fetching bin history logs:", err);
    }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [binsData, alertsData] = await Promise.all([
        api.getBins(),
        api.getAlerts().catch((err) => {
          // Restricted roles (e.g. drivers) might get 403 on alerts, handle gracefully
          if (err.message.includes("403")) return [];
          throw err;
        }),
      ]);

      setBins(binsData);
      setAlerts(alertsData);

      // Dynamically refresh selected bin's history
      if (selectedBin) {
        fetchHistory(selectedBin.bin_id);
      }
    } catch (err) {
      console.error("Dashboard live polling cycle failed:", err);
      if (err.message.includes("401") || err.message.includes("credentials")) {
        logout(); // Session expired or invalid token
      }
    } finally {
      setLoading(false);
    }
  }, [selectedBin, fetchHistory, logout]);

  const acknowledgeAlert = async (alertId, operatorName) => {
    try {
      await api.acknowledgeAlert(alertId, operatorName);
      await fetchData();
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
      await fetchData();
      if (selectedBin?.bin_id === binId) {
        await fetchHistory(binId);
      }
    } catch (err) {
      console.error("Failed manual empty override transaction:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  const selectBin = (bin) => {
    setSelectedBin(bin);
    fetchHistory(bin.bin_id);
  };

  return {
    bins,
    alerts,
    selectedBin,
    history,
    loading,
    refreshData: fetchData,
    selectBin,
    acknowledgeAlert,
    handleManualEmpty,
  };
}
