// frontend/src/components/AlertList.jsx
// -------------------------------------------------------------------------
// Premium AlertList Component - Dynamic responsive warning monitor
// -------------------------------------------------------------------------

import React from "react";
import { AlertTriangle, ShieldCheck, CheckCircle } from "lucide-react";

export default function AlertList({ alerts, userRole, onAcknowledge }) {
  if (userRole === "driver") return null;

  return (
    <section className="bg-slate-900/30 border border-slate-800/80 p-5 rounded-3xl shadow-2xl backdrop-blur-md flex-1 flex flex-col relative overflow-hidden transition-all duration-300">
      {/* Background design glow */}
      <div className="absolute -top-10 -left-10 w-32 h-32 bg-red-500/5 rounded-full blur-2xl pointer-events-none"></div>

      <div className="flex items-center space-x-2.5 mb-5 border-b border-slate-800/40 pb-4">
        <div className="p-1.5 bg-red-500/10 rounded-lg border border-red-500/20">
          <AlertTriangle className="h-5 w-5 text-red-400" />
        </div>
        <h2 className="text-sm font-black tracking-widest text-slate-300 uppercase">
          Warning Center ({alerts.length})
        </h2>
      </div>

      {alerts.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
          <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-3xl mb-4 shadow-inner">
            <CheckCircle className="h-10 w-10 text-emerald-400/30 animate-pulse" />
          </div>
          <span className="text-emerald-400/80 font-bold tracking-widest text-xs uppercase">
            All Nodes Cleared
          </span>
          <span className="text-[10px] text-slate-600 mt-1 max-w-[180px] leading-relaxed">
            Fleet grid is functioning within safe thresholds.
          </span>
        </div>
      ) : (
        <div className="space-y-4 overflow-y-auto flex-1 max-h-[500px] pr-1 scrollbar-thin scrollbar-thumb-slate-800">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="p-4 bg-slate-950/40 border border-slate-800/60 rounded-2xl flex flex-col justify-between shadow-inner relative overflow-hidden hover:border-red-500/30 transition-all duration-300"
            >
              <div className="flex items-start space-x-3">
                <div className="relative mt-0.5">
                  <div className="absolute top-0 left-0 h-4 w-4 rounded-full bg-red-500/30 animate-ping"></div>
                  <AlertTriangle className="h-4 w-4 text-red-500 relative z-10" />
                </div>
                <div>
                  <h4 className="font-extrabold text-xs text-slate-200 uppercase tracking-wider">
                    Capacity Breach
                  </h4>
                  <div className="flex items-center space-x-1.5 text-[10px] text-slate-500 mt-0.5">
                    <span>Node ID:</span>
                    <span className="font-mono font-bold text-red-400/80">
                      {alert.bin_id}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/30 flex justify-between items-center text-[10px] text-slate-500 font-semibold">
                <span className="font-medium">
                  Triggered: {new Date(alert.triggered_at).toLocaleTimeString()}
                </span>

                {alert.acknowledged_by ? (
                  <span className="flex items-center text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-lg text-[9px] font-black tracking-widest uppercase">
                    <ShieldCheck className="h-3 w-3 mr-1" /> ACK'D
                  </span>
                ) : (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="bg-red-500/10 hover:bg-red-500 border border-red-500/20 text-red-400 hover:text-white px-3 py-1 rounded-lg text-[9px] font-black tracking-widest uppercase transition-all duration-300 transform hover:-translate-y-0.5 active:translate-y-0"
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
