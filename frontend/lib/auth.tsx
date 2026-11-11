"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokens } from "./api";

export type Me = {
  user: { id: string; email: string; full_name: string; role: string; hospital_id: string | null; must_change_password: boolean; medical_registration_no: string };
  hospital: { id: string; name: string; code: string; brand_color: string; plan_code: string; licence_status: string; has_logo: boolean } | null;
  permissions: string[];
};

type Ctx = { me: Me | null; loading: boolean; can: (p: string) => boolean; reload: () => Promise<void>; logout: () => Promise<void> };
const AuthCtx = createContext<Ctx>({ me: null, loading: true, can: () => false, reload: async () => {}, logout: async () => {} });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!tokens.access) { setMe(null); setLoading(false); return; }
    try { setMe(await api<Me>("/auth/me")); } catch { setMe(null); } finally { setLoading(false); }
  }, []);
  useEffect(() => { reload(); }, [reload]);
  const logout = async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch {}
    tokens.clear(); setMe(null); window.location.href = "/login";
  };
  return (
    <AuthCtx.Provider value={{ me, loading, reload, logout, can: (p) => !!me?.permissions.includes(p) }}>
      {children}
    </AuthCtx.Provider>
  );
}
export const useAuth = () => useContext(AuthCtx);
