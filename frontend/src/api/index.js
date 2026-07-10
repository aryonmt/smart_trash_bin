// frontend/src/api/index.js
// -------------------------------------------------------------------------
// Centralized API client for interacting with the backend gateway
// -------------------------------------------------------------------------

const API_BASE_URL = `http://${window.location.hostname}:8000`;

/**
 * Constructs the authorization headers required for protected endpoints.
 * @returns {HeadersInit} - The headers object with the bearer token.
 */
const getAuthHeaders = () => {
  const token = sessionStorage.getItem("token");
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
};

/**
 * Handles API responses, automatically parsing JSON or throwing network errors.
 * @param {Response} response - The raw fetch response object.
 * @returns {Promise<any>} - The parsed JSON data.
 */
const handleResponse = async (response) => {
  if (!response.ok) {
    let errorDetail = `HTTP Error: ${response.statusText}`;
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorDetail;
    } catch (e) {
      // Ignore if response body is not JSON
    }
    throw new Error(errorDetail);
  }
  return response.json();
};

export const api = {
  login: async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    return handleResponse(response);
  },

  getBins: async () => {
    const response = await fetch(`${API_BASE_URL}/api/bins`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  getBinHistory: async (binId) => {
    const response = await fetch(`${API_BASE_URL}/api/bins/${binId}/history`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  getAlerts: async () => {
    const response = await fetch(`${API_BASE_URL}/api/alerts`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  acknowledgeAlert: async (alertId, operatorName) => {
    const response = await fetch(
      `${API_BASE_URL}/api/alerts/${alertId}/acknowledge`,
      {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ operator_name: operatorName }),
      },
    );
    return handleResponse(response);
  },

  manualEmptyBin: async (binId) => {
    const response = await fetch(`${API_BASE_URL}/api/bins/${binId}/empty`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  registerBin: async (binData) => {
    const response = await fetch(`${API_BASE_URL}/api/bins`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(binData),
    });
    return handleResponse(response);
  },
};
