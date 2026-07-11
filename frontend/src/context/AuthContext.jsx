// frontend/src/context/AuthContext.jsx
// -------------------------------------------------------------------------
// Global state management provider for user authentication session
// -------------------------------------------------------------------------

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = sessionStorage.getItem("token");
    const username = sessionStorage.getItem("username");
    const role = sessionStorage.getItem("role");

    if (token && username && role) {
      setUser({ token, username, role });
    }
  }, []);

  // Wrap in useCallback to preserve function reference across renders
  const login = useCallback((userData) => {
    sessionStorage.setItem("token", userData.access_token);
    sessionStorage.setItem("username", userData.username);
    sessionStorage.setItem("role", userData.role);
    setUser({
      token: userData.access_token,
      username: userData.username,
      role: userData.role,
    });
  }, []);

  // Wrap in useCallback to preserve function reference across renders
  const logout = useCallback(() => {
    sessionStorage.clear();
    setUser(null);
  }, []);

  // Wrap in useMemo to prevent unnecessary context re-renders
  const authValue = useMemo(
    () => ({
      user,
      login,
      logout,
      isAuthenticated: !!user,
    }),
    [user, login, logout],
  );

  return (
    <AuthContext.Provider value={authValue}>{children}</AuthContext.Provider>
  );
};

export const useAuth = () => {
  return useContext(AuthContext);
};
