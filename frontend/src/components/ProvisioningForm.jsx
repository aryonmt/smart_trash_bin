// frontend/src/components/ProvisioningForm.jsx
// -------------------------------------------------------------------------
// Premium ProvisioningForm Component - Responsive glassmorphic panel
// -------------------------------------------------------------------------

import React, { useState } from "react";
import { Trash2, AlertTriangle, ShieldCheck, Cpu } from "lucide-react";
import { api } from "../api";

export default function ProvisioningForm({ onRegistrationSuccess }) {
  const [newBinId, setNewBinId] = useState("");
  const [newZoneId, setNewZoneId] = useState("");
  const [newDepth, setNewDepth] = useState(150);
  const [newLabel, setNewLabel] = useState("");
  const [newLat, setNewLat] = useState("");
  const [newLng, setNewLng] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    const binPayload = {
      bin_id: newBinId.trim().toLowerCase(),
      zone_id: newZoneId.trim().toLowerCase(),
      bin_depth_cm: parseFloat(newDepth),
      label: newLabel.trim() || null,
      latitude: newLat ? parseFloat(newLat) : null,
      longitude: newLng ? parseFloat(newLng) : null,
    };

    try {
      await api.registerBin(binPayload);
      setSuccessMsg(`Bin ${newBinId} successfully provisioned on server!`);
      setNewBinId("");
      setNewZoneId("");
      setNewLabel("");
      setNewLat("");
      setNewLng("");
      onRegistrationSuccess();
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  return (
    <section className="bg-slate-900/30 border border-slate-800/80 p-6 rounded-3xl shadow-2xl backdrop-blur-md relative overflow-hidden transition-all duration-300">
      {/* Decorative background glow */}
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-emerald-500/5 rounded-full blur-2xl pointer-events-none"></div>

      <div className="flex items-center space-x-2.5 mb-5 border-b border-slate-800/40 pb-4">
        <div className="p-1.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
          <Cpu className="h-5 w-5 text-emerald-400" />
        </div>
        <h3 className="text-emerald-400 font-black text-lg tracking-wider uppercase">
          Provision New Node
        </h3>
      </div>

      {errorMsg && (
        <div className="bg-red-500/5 border border-red-500/20 text-red-400 text-xs p-3.5 rounded-xl mb-5 flex items-center space-x-2 backdrop-blur-md">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span className="font-semibold">{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-500/5 border border-emerald-500/20 text-emerald-400 text-xs p-3.5 rounded-xl mb-5 flex items-center space-x-2 backdrop-blur-md">
          <ShieldCheck className="h-4 w-4 flex-shrink-0 animate-bounce" />
          <span className="font-semibold">{successMsg}</span>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 md:grid-cols-3 gap-5"
      >
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Bin ID *
          </label>
          <input
            type="text"
            required
            value={newBinId}
            onChange={(e) => setNewBinId(e.target.value)}
            placeholder="e.g. bin-0143"
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium placeholder:text-slate-600"
          />
        </div>
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Zone ID *
          </label>
          <input
            type="text"
            required
            value={newZoneId}
            onChange={(e) => setNewZoneId(e.target.value)}
            placeholder="e.g. district-7"
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium placeholder:text-slate-600"
          />
        </div>
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Bin Depth (CM) *
          </label>
          <input
            type="number"
            required
            value={newDepth}
            onChange={(e) => setNewDepth(e.target.value)}
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium"
          />
        </div>
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Label (Location)
          </label>
          <input
            type="text"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="e.g. Central Library Corner"
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium placeholder:text-slate-600"
          />
        </div>
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Latitude
          </label>
          <input
            type="number"
            step="any"
            value={newLat}
            onChange={(e) => setNewLat(e.target.value)}
            placeholder="e.g. 35.7001"
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium placeholder:text-slate-600"
          />
        </div>
        <div>
          <label className="block text-slate-400 text-[10px] font-bold tracking-widest mb-1.5 uppercase">
            Longitude
          </label>
          <input
            type="number"
            step="any"
            value={newLng}
            onChange={(e) => setNewLng(e.target.value)}
            placeholder="e.g. 51.4002"
            className="w-full bg-slate-950/60 border border-slate-800/60 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/15 transition-all font-medium placeholder:text-slate-600"
          />
        </div>

        <div className="md:col-span-3 flex justify-end pt-3 border-t border-slate-800/20 mt-1">
          <button
            type="submit"
            className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-3 px-8 rounded-xl text-xs tracking-widest uppercase transition-all duration-300 shadow-md shadow-emerald-500/10 hover:shadow-emerald-500/20 transform hover:-translate-y-0.5 active:translate-y-0"
          >
            Authorize and Register Bin
          </button>
        </div>
      </form>
    </section>
  );
}
