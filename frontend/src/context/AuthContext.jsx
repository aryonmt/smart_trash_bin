// frontend/src/context/AuthContext.jsx
// -------------------------------------------------------------------------
// Global state management provider for user authentication session
// -------------------------------------------------------------------------

import React, { createContext, useContext, useState, useEffect } from "react";

const AuthContext = createContext(null);

/**
 * Provides authentication state and functions to its children components.
 */
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  // On initial app load, check session storage for existing authentication
  useEffect(() => {
    const token = sessionStorage.getItem("token");
    const username = sessionStorage.getItem("username");
    const role = sessionStorage.getItem("role");

    if (token && username && role) {
      setUser({ token, username, role });
    }
  }, []);

  const login = (userData) => {
    sessionStorage.setItem("token", userData.access_token);
    sessionStorage.setItem("username", userData.username);
    sessionStorage.setItem("role", userData.role);
    setUser({
      token: userData.access_token,
      username: userData.username,
      role: userData.role,
    });
  };

  const logout = () => {
    sessionStorage.clear();
    setUser(null);
  };

  const authValue = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
  );
};

/**
 * Custom hook to easily access authentication context from any component.
 */
export const useAuth = () => {
  return useContext(AuthContext);
};
