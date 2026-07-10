// frontend/src/components/ProvisioningForm.jsx
// -------------------------------------------------------------------------
// ProvisioningForm Component - Renders device registration form for admins
// -------------------------------------------------------------------------

import React, { useState } from "react";
import { Trash2 } from "lucide-react";
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
      bin_id: newBinId,
      zone_id: newZoneId,
      bin_depth_cm: parseFloat(newDepth),
      label: newLabel || null,
      latitude: newLat ? parseFloat(newLat) : null,
      longitude: newLng ? parseFloat(newLng) : null,
    };

    try {
      await api.registerBin(binPayload);
      setSuccessMsg(`Bin ${newBinId} successfully provisioned!`);
      setNewBinId("");
      setNewZoneId("");
      setNewLabel("");
      setNewLat("");
      setNewLng("");
      onRegistrationSuccess(); // Trigger parent refresh
    } catch (err) {
      setErrorMsg(err.message);
    }
  };

  return (
    <section className="bg-gray-900 border border-gray-800 p-6 rounded-2xl shadow-xl transition-all duration-300">
      <h3 className="text-emerald-400 font-bold text-lg mb-4 flex items-center gap-2">
        <Trash2 className="h-5 w-5" />
        Provision New Smart Bin
      </h3>

      {errorMsg && (
        <div className="bg-red-500/10 border border-red-500 text-red-400 text-xs p-2.5 rounded-lg mb-4 text-center">
          {errorMsg}
        </div>
      )}
      {successMsg && (
        <div className="bg-emerald-500/10 border border-emerald-500 text-emerald-400 text-xs p-2.5 rounded-lg mb-4 text-center">
          {successMsg}
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            BIN ID *
          </label>
          <input
            type="text"
            required
            value={newBinId}
            onChange={(e) => setNewBinId(e.target.value)}
            placeholder="e.g. bin-0143"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            ZONE ID *
          </label>
          <input
            type="text"
            required
            value={newZoneId}
            onChange={(e) => setNewZoneId(e.target.value)}
            placeholder="e.g. district-7"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            BIN DEPTH (CM) *
          </label>
          <input
            type="number"
            required
            value={newDepth}
            onChange={(e) => setNewDepth(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            LABEL (LOCATION)
          </label>
          <input
            type="text"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="e.g. Central Library Corner"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            LATITUDE
          </label>
          <input
            type="number"
            step="any"
            value={newLat}
            onChange={(e) => setNewLat(e.target.value)}
            placeholder="e.g. 35.7001"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>
        <div>
          <label className="block text-gray-400 text-[10px] font-bold mb-1">
            LONGITUDE
          </label>
          <input
            type="number"
            step="any"
            value={newLng}
            onChange={(e) => setNewLng(e.target.value)}
            placeholder="e.g. 51.4002"
            className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="md:col-span-3 flex justify-end pt-2">
          <button
            type="submit"
            className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-2.5 px-6 rounded-lg text-xs transition duration-200 shadow-md shadow-emerald-500/10"
          >
            Authorize and Register Bin
          </button>
        </div>
      </form>
    </section>
  );
}
