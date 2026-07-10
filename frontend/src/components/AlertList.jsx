// frontend/src/components/AlertList.jsx
// -------------------------------------------------------------------------
// AlertList Component - Displays active high-fill threshold warnings
// -------------------------------------------------------------------------

import React from "react";
import { AlertTriangle, CheckCircle } from "lucide-react";

export default function AlertList({ alerts, userRole, onAcknowledge }) {
  // Security restriction: Drivers are not allowed to inspect system warnings
  if (userRole === "driver") return null;

  return (
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
                  Triggered: {new Date(alert.triggered_at).toLocaleTimeString()}
                </span>
                {alert.acknowledged_by ? (
                  <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded font-medium">
                    Ack'd: {alert.acknowledged_by}
                  </span>
                ) : (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
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
  );
}
