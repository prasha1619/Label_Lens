import React, { createContext, useContext, useEffect, useState } from "react";
import { ApiError } from "../services/api";
import { authService, User } from "../services/authService";
type AuthValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
    organization?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
};
const AuthContext = createContext<AuthValue | null>(null);
export const AuthProvider: React.FC<React.PropsWithChildren> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    authService
      .me()
      .then(setUser)
      .catch((e) => {
        if (!(e instanceof ApiError) || e.status !== 401)
          console.warn("Could not restore session");
      })
      .finally(() => setLoading(false));
  }, []);
  const login = async (email: string, password: string) =>
    setUser((await authService.login(email, password)).user);
  const register = async (data: any) =>
    setUser((await authService.register(data)).user);
  const logout = async () => {
    await authService.logout();
    setUser(null);
  };
  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, setUser }}
    >
      {children}
    </AuthContext.Provider>
  );
};
export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
};
