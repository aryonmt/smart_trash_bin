// frontend/src/components/BinCard.jsx
// -------------------------------------------------------------------------
// BinCard Component - Renders status and progress metrics of a single bin
// -------------------------------------------------------------------------

import React from "react";
import { Wifi, WifiOff } from "lucide-react";

export default function BinCard({ bin, selectedBin, onSelect }) {
  const isOnline = bin.status === "online";
  const isSelected = selectedBin?.bin_id === bin.bin_id;

  const getFillColor = (pct) => {
    if (pct >= 80) return "bg-red-500 text-red-500 border-red-500";
    if (pct >= 50) return "bg-yellow-500 text-yellow-500 border-yellow-500";
    return "bg-green-500 text-green-500 border-green-500";
  };

  const fillColorClass = getFillColor(bin.current_fill_pct);

  return (
    <div
      onClick={() => onSelect(bin)}
      className={`p-4 rounded-xl border transition cursor-pointer hover:scale-[1.02] flex flex-col justify-between h-44 ${
        isSelected
          ? "bg-gray-800 border-emerald-500"
          : "bg-gray-900 border-gray-800"
      }`}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg">{bin.bin_id}</h3>
          <span className="text-xs text-gray-400 font-medium px-2 py-0.5 bg-gray-800 rounded">
            {bin.zone_id}
          </span>
        </div>
        <div>
          {isOnline ? (
            <span className="flex items-center text-[10px] text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full font-semibold">
              <Wifi className="h-3 w-3 mr-1" /> Online
            </span>
          ) : (
            <span className="flex items-center text-[10px] text-gray-400 bg-gray-500/10 px-2 py-0.5 rounded-full font-semibold">
              <WifiOff className="h-3 w-3 mr-1" /> Offline
            </span>
          )}
        </div>
      </div>

      {/* Fill Level Progress Indicator */}
      <div className="my-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-gray-400">Fill level</span>
          <span className={`font-bold ${fillColorClass.split(" ")[1]}`}>
            {bin.current_fill_pct !== null ? `${bin.current_fill_pct}%` : "0%"}
          </span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${fillColorClass.split(" ")[0]}`}
            style={{ width: `${bin.current_fill_pct || 0}%` }}
          ></div>
        </div>
      </div>

      <div className="text-[11px] text-gray-400 flex justify-between">
        <span>
          Last Update:{" "}
          {bin.last_reading_at
            ? new Date(bin.last_reading_at).toLocaleTimeString()
            : "N/A"}
        </span>
        {bin.last_emptied_at && (
          <span className="text-emerald-400 font-medium">Emptied</span>
        )}
      </div>
    </div>
  );
}
