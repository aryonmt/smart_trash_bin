// frontend/src/components/BinCard.jsx
// -------------------------------------------------------------------------
// Premium Interactive BinCard - Displays fill level progress and live status
// -------------------------------------------------------------------------

import React from "react";
import { Wifi, WifiOff, MapPin, Clock } from "lucide-react";

export default function BinCard({ bin, selectedBin, onSelect }) {
  const isOnline = bin.status === "online";
  const isSelected = selectedBin?.bin_id === bin.bin_id;

  // Determine color tokens based on current fill percentage
  const getFillColor = (pct) => {
    if (pct >= 80) {
      return {
        bar: "bg-gradient-to-r from-red-600 to-rose-400 shadow-[0_0_12px_rgba(239,68,68,0.5)]",
        text: "text-red-400",
        glow: "shadow-[0_0_20px_rgba(239,68,68,0.15)] border-red-500/30 hover:border-red-500/50",
      };
    }
    if (pct >= 50) {
      return {
        bar: "bg-gradient-to-r from-amber-500 to-yellow-400 shadow-[0_0_12px_rgba(245,158,11,0.5)]",
        text: "text-amber-400",
        glow: "shadow-[0_0_20px_rgba(245,158,11,0.1)] border-amber-500/30 hover:border-amber-500/50",
      };
    }
    return {
      bar: "bg-gradient-to-r from-emerald-500 to-teal-400 shadow-[0_0_12px_rgba(16,185,129,0.5)]",
      text: "text-emerald-400",
      glow: "shadow-[0_0_20px_rgba(16,185,129,0.1)] border-emerald-500/20 hover:border-emerald-500/40",
    };
  };

  const colors = getFillColor(bin.current_fill_pct);
  const fillPercent =
    bin.current_fill_pct !== null ? bin.current_fill_pct : 0.0;

  return (
    <div
      onClick={() => onSelect(bin)}
      className={`p-5 rounded-2xl border transition-all duration-300 cursor-pointer transform hover:-translate-y-1 ${colors.glow} ${
        isSelected
          ? "bg-slate-900/80 border-emerald-500/80 shadow-[0_0_30px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/20"
          : "bg-slate-900/40 border-slate-800/80"
      }`}
    >
      {/* Top Row: Bin ID and Status Badges */}
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <h3 className="font-black text-xl tracking-wide text-white group-hover:text-emerald-400 transition-colors">
            {bin.bin_id}
          </h3>
          <div className="flex items-center space-x-1.5 text-slate-500">
            <MapPin className="h-3 w-3 text-slate-500" />
            <span className="text-[10px] font-bold tracking-widest uppercase">
              {bin.zone_id}
            </span>
          </div>
        </div>

        <div>
          {isOnline ? (
            <span className="flex items-center text-[10px] text-green-400 bg-green-500/10 border border-green-500/20 px-2.5 py-1 rounded-full font-semibold">
              <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse mr-1.5"></span>
              <Wifi className="h-3 w-3 mr-1" /> ONLINE
            </span>
          ) : (
            <span className="flex items-center text-[10px] text-slate-500 bg-slate-500/5 border border-slate-800/50 px-2.5 py-1 rounded-full font-semibold">
              <WifiOff className="h-3 w-3 mr-1" /> OFFLINE
            </span>
          )}
        </div>
      </div>

      {/* Middle Row: Progress Bar and Percentage */}
      <div className="my-4">
        <div className="flex justify-between text-xs mb-1.5 font-bold">
          <span className="text-slate-400 tracking-wider">
            Garbage Capacity
          </span>
          <span className={colors.text}>{fillPercent}%</span>
        </div>
        <div className="w-full bg-slate-950/60 rounded-full h-2.5 p-0.5 border border-slate-800/40">
          <div
            className={`h-1.5 rounded-full transition-all duration-700 ease-out ${colors.bar}`}
            style={{ width: `${fillPercent}%` }}
          ></div>
        </div>
      </div>

      {/* Bottom Row: Last updated timestamp */}
      <div className="text-[10px] text-slate-500 flex justify-between items-center border-t border-slate-800/30 pt-3 mt-1.5">
        <div className="flex items-center space-x-1">
          <Clock className="h-3 w-3 text-slate-600" />
          <span>
            Updated:{" "}
            {bin.last_reading_at
              ? new Date(bin.last_reading_at).toLocaleTimeString()
              : "N/A"}
          </span>
        </div>
        {bin.last_emptied_at && (
          <span className="text-emerald-400/80 bg-emerald-500/5 border border-emerald-500/10 px-2 py-0.5 rounded font-bold tracking-widest text-[9px] uppercase">
            CLEARED
          </span>
        )}
      </div>
    </div>
  );
}
